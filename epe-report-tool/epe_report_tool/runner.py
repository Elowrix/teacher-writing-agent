from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from .analytics import (
    EPEAnalyzer,
    build_band_table,
    build_faculty_scholarship_table,
    build_near_miss_table,
    build_result_table,
    build_skill_table,
    build_threshold_group_table,
    build_validation_table,
    normalize_text,
)
from .extra_tables import (
    add_cell_size_flag,
    build_exam_type_table,
    build_faculty_near_miss_table,
    build_near_miss_limitations,
    build_participation_table,
    build_quality_issue_table,
    build_question_coverage_table,
    build_threshold_concentration_table,
)
from .registry_enrichment import enrich_from_registries
from .registry_jan2024 import load_january_2024_from_registry
from .report_writer import write_excel, write_powerpoint, write_word
from .scope import apply_analysis_scope, build_exclusion_table


class ReportRunner:
    """Dashboard-free EPE analysis and report production pipeline."""

    def __init__(self, project_root: Path, hmac_secret: str) -> None:
        self.project_root = project_root
        self.hmac_secret = hmac_secret

    def run(
        self,
        *,
        epe_files: Iterable[Path],
        registry_files: Iterable[Path],
        output_dir: Path,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        epe_files = list(epe_files)
        registry_files = list(registry_files)

        analyzer = EPEAnalyzer(self.hmac_secret)
        master, source_quality = analyzer.load_files(epe_files)
        registry_inventory = self._inventory_registry_files(registry_files)

        original_jan_present = (
            not master.empty
            and "analysis_exam_id" in master
            and master["analysis_exam_id"].eq("2023-24_OCAK").any()
        )
        if not original_jan_present:
            jan_frame, jan_quality = self._load_january_2024(registry_files)
            if not jan_frame.empty:
                master = pd.concat([master, jan_frame], ignore_index=True, sort=False) if not master.empty else jan_frame
                master = analyzer._apply_last_sitting_rule(master)
                master = analyzer._derive_fields(master)
            if jan_quality:
                source_quality = pd.concat([source_quality, pd.DataFrame([jan_quality])], ignore_index=True, sort=False)

        if master.empty:
            details = "\n".join(
                f"- {row.get('file', '—')}: {row.get('status', '—')} / {row.get('note', '')}"
                for _, row in source_quality.iterrows()
            )
            raise ValueError(
                "Seçilen dosyalardan analiz tablosu üretilemedi. Dosya adlarını, sayfaları ve sütunları kontrol edin.\n"
                + details
            )

        master, registry_join_audit, registry_match_audit = enrich_from_registries(
            master,
            registry_files,
            self.hmac_secret,
        )
        master = analyzer._derive_fields(master)

        scoped_master = apply_analysis_scope(master)
        analysis_master = scoped_master[scoped_master["analysis_include"]].copy()
        excluded_table = build_exclusion_table(scoped_master)

        result_table = build_result_table(analysis_master)
        near_table = build_near_miss_table(analysis_master)
        faculty_burs = build_faculty_scholarship_table(analysis_master)
        if not faculty_burs.empty:
            faculty_burs = add_cell_size_flag(faculty_burs, "N")

        tables: dict[str, pd.DataFrame] = {
            "Katilim Ozeti": build_participation_table(analysis_master),
            "Genel Sonuclar": result_table,
            "Near Miss": near_table,
            "Near Miss Sinirlilik": build_near_miss_limitations(analysis_master, near_table),
            "Bantlar": build_band_table(analysis_master),
            "Esik Yogunlugu": build_threshold_concentration_table(analysis_master),
            "Esik Gruplari": build_threshold_group_table(analysis_master),
            "Fakulte Near Miss": build_faculty_near_miss_table(analysis_master),
            "Fakulte Burs": faculty_burs,
            "Beceri Profili": build_skill_table(analysis_master),
            "Sinav Turu": build_exam_type_table(analysis_master),
            "Dogrulama": build_validation_table(analysis_master),
            "Dislanan Kayitlar": excluded_table,
            "Kutuk Esleme": registry_match_audit,
            "Kutuk Okuma": registry_join_audit,
            "Kaynak Kalitesi": source_quality,
            "Kutuk Envanteri": registry_inventory,
            "Master Ozet": self._master_summary(scoped_master),
        }
        tables["Kalite Sorunlari"] = build_quality_issue_table(
            source_quality,
            registry_match_audit,
            registry_join_audit,
        )
        tables["12 Soru Kapsami"] = build_question_coverage_table(tables)

        coverage_note = self._coverage_note(scoped_master, source_quality, registry_inventory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = output_dir / f"EPE_Analiz_Tablolari_{timestamp}.xlsx"
        word_path = output_dir / f"EPE_Yillar_Arasi_Analiz_Raporu_{timestamp}.docx"
        ppt_path = output_dir / f"EPE_Yonetim_Sunumu_{timestamp}.pptx"
        log_path = output_dir / f"EPE_Calisma_Gunlugu_{timestamp}.txt"

        write_excel(excel_path, tables)
        write_word(word_path, tables, coverage_note)
        write_powerpoint(ppt_path, tables, coverage_note)
        self._write_log(log_path, epe_files, registry_files, tables, coverage_note)

        return {
            "Excel analiz tabloları": excel_path,
            "Word raporu": word_path,
            "PowerPoint sunumu": ppt_path,
            "Çalışma günlüğü": log_path,
        }

    def _load_january_2024(self, registry_files: list[Path]) -> tuple[pd.DataFrame, dict[str, object] | None]:
        candidates = [
            path for path in registry_files
            if "2023 2024" in normalize_text(path.stem).replace("-", " ").replace("_", " ")
            or "2023-2024" in path.stem
        ]
        if not candidates:
            return pd.DataFrame(), None
        try:
            return load_january_2024_from_registry(candidates[0], self.hmac_secret)
        except Exception as exc:  # noqa: BLE001
            return pd.DataFrame(), {
                "file": candidates[0].name,
                "analysis_exam_id": "2023-24_OCAK",
                "source_session_id": "2023-24_OCAK_REGISTRY",
                "status": "REGISTRY_ADAPTER_ERROR",
                "note": str(exc),
            }

    @staticmethod
    def _inventory_registry_files(paths: Iterable[Path]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for path in paths:
            if not path.exists():
                rows.append({"file": path.name, "status": "ERROR", "sheet": "—", "rows": 0, "columns": 0, "note": "Dosya bulunamadı"})
                continue
            try:
                workbook = pd.ExcelFile(path)
            except Exception as exc:  # noqa: BLE001
                rows.append({"file": path.name, "status": "ERROR", "sheet": "—", "rows": 0, "columns": 0, "note": str(exc)})
                continue
            for sheet in workbook.sheet_names:
                try:
                    frame = pd.read_excel(path, sheet_name=sheet, header=None)
                    rows.append({"file": path.name, "status": "OK", "sheet": sheet,
                                 "rows": int(frame.shape[0]), "columns": int(frame.shape[1]), "note": ""})
                except Exception as exc:  # noqa: BLE001
                    rows.append({"file": path.name, "status": "ERROR", "sheet": sheet, "rows": 0, "columns": 0, "note": str(exc)})
        return pd.DataFrame(rows)

    @staticmethod
    def _master_summary(master: pd.DataFrame) -> pd.DataFrame:
        if master.empty:
            return pd.DataFrame()
        work = master.copy()
        work["skill_complete"] = work[["booklet", "writing", "speaking"]].notna().all(axis=1)
        if "analysis_include" not in work:
            work["analysis_include"] = True
        if "registry_match" not in work:
            work["registry_match"] = False
        return (
            work.groupby(["analysis_exam_id", "academic_year", "slot"], dropna=False)
            .agg(
                source_row_n=("student_hash", "size"),
                analysis_included_n=("analysis_include", "sum"),
                excluded_n=("analysis_include", lambda s: int((~s).sum())),
                registry_matched_n=("registry_match", "sum"),
                official_result_n=("official_result", lambda s: int(s.isin(["PASS", "FAIL"]).sum())),
                decision_score_n=("decision_score", "count"),
                skill_complete_n=("skill_complete", "sum"),
            )
            .reset_index()
        )

    @staticmethod
    def _coverage_note(master: pd.DataFrame, quality: pd.DataFrame, registry_inventory: pd.DataFrame) -> str:
        exams = sorted(master["analysis_exam_id"].dropna().astype(str).unique().tolist()) if not master.empty else []
        recognized_files = int(quality["status"].isin(["OK", "PARTIAL_DERIVED"]).sum()) if not quality.empty and "status" in quality else 0
        registry_files = int(registry_inventory["file"].nunique()) if not registry_inventory.empty else 0
        excluded_n = int((~master["analysis_include"]).sum()) if not master.empty and "analysis_include" in master else 0
        included_n = int(master["analysis_include"].sum()) if not master.empty and "analysis_include" in master else len(master)
        matched_n = int(master.get("registry_match", pd.Series(False, index=master.index)).fillna(False).sum()) if not master.empty else 0
        note = (
            f"Bu çalıştırmada {recognized_files} kaynak tanındı; {len(exams)} analiz oturumu üretildi "
            f"({', '.join(exams) if exams else 'yok'}). Ayrıca {registry_files} öğrenci kütüğü okundu ve "
            f"{matched_n} EPE kaydı öğrenci numarasının güvenli özeti üzerinden kütükle eşleştirildi. "
            f"Ana lisans analizine {included_n} kayıt dahil edildi; yüksek lisans, doktora veya dismissed statüsündeki "
            f"{excluded_n} kayıt ana tablolardan çıkarılarak ayrı denetim tablosunda tutuldu."
        )
        original_jan = (
            not master.empty
            and master["analysis_exam_id"].eq("2023-24_OCAK").any()
            and master.loc[master["analysis_exam_id"].eq("2023-24_OCAK"), "skill_complete"].any()
            if "skill_complete" in master else False
        )
        if original_jan:
            note += " Ocak 2024 orijinal birleşik EPE dosyasıyla toplam, karar puanı ve beceri analizlerine tam olarak dahildir."
        elif "2023-24_OCAK" in exams:
            note += (
                " Ocak 2024 genel sonuç, bant ve near-miss analizlerine 2023–2024 öğrenci kütüğünden türetilen "
                "karar puanıyla dahildir; orijinal EPE dosyası olmadığı için beceri analizine dahil değildir."
            )
        else:
            note += " Ocak 2024 bu çalıştırmada analize eklenememiştir."
        return note

    @staticmethod
    def _write_log(
        path: Path,
        epe_files: list[Path],
        registry_files: list[Path],
        tables: dict[str, pd.DataFrame],
        coverage_note: str,
    ) -> None:
        lines = [
            "EPE RAPORLAMA ARACI - ÇALIŞMA GÜNLÜĞÜ",
            "",
            coverage_note,
            "",
            "EPE DOSYALARI:",
            *[f"- {path}" for path in epe_files],
            "",
            "ÖĞRENCİ KÜTÜKLERİ:",
            *[f"- {path}" for path in registry_files],
            "",
            "ÜRETİLEN TABLOLAR:",
            *[f"- {name}: {len(frame)} satır" for name, frame in tables.items()],
            "",
            "NOT: Resmî PASS/FAIL sonucu araç tarafından değiştirilmez.",
            "NOT: Fakülte, bölüm, burs ve giriş yılı alanları mümkün olduğunda yıllık öğrenci kütüğünden tamamlanır.",
            "NOT: Yüksek lisans, doktora ve dismissed kayıtları ana lisans analizinden çıkarılır; Dislanan Kayitlar tablosunda toplu olarak gösterilir.",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
