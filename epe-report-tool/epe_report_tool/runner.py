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
)
from .report_writer import write_excel, write_powerpoint, write_word


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

        if master.empty:
            recognized = source_quality[source_quality.get("status", pd.Series(dtype=str)).eq("OK")] if not source_quality.empty else pd.DataFrame()
            if recognized.empty:
                details = "\n".join(
                    f"- {row.get('file', '—')}: {row.get('status', '—')} / {row.get('note', '')}"
                    for _, row in source_quality.iterrows()
                )
                raise ValueError(
                    "Seçilen EPE dosyalarından analiz tablosu üretilemedi. "
                    "Dosya adlarının eşleme tablosundaki adlarla uyumlu olduğunu kontrol edin.\n" + details
                )

        tables: dict[str, pd.DataFrame] = {
            "Genel Sonuclar": build_result_table(master),
            "Near Miss": build_near_miss_table(master),
            "Bantlar": build_band_table(master),
            "Esik Gruplari": build_threshold_group_table(master),
            "Fakulte Burs": build_faculty_scholarship_table(master),
            "Beceri Profili": build_skill_table(master),
            "Dogrulama": build_validation_table(master),
            "Kaynak Kalitesi": source_quality,
            "Kutuk Envanteri": registry_inventory,
            "Master Ozet": self._master_summary(master),
        }

        coverage_note = self._coverage_note(master, source_quality, registry_inventory)
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
        return (
            master.groupby(["analysis_exam_id", "academic_year", "slot"], dropna=False)
            .agg(
                row_n=("student_hash", "size"),
                official_result_n=("official_result", lambda s: int(s.isin(["PASS", "FAIL"]).sum())),
                decision_score_n=("decision_score", "count"),
                skill_complete_n=("student_hash", lambda s: 0),
            )
            .reset_index()
            .assign(
                skill_complete_n=lambda frame: frame["analysis_exam_id"].map(
                    master.assign(skill_complete=master[["booklet", "writing", "speaking"]].notna().all(axis=1))
                    .groupby("analysis_exam_id")["skill_complete"].sum()
                ).fillna(0).astype(int)
            )
        )

    @staticmethod
    def _coverage_note(master: pd.DataFrame, quality: pd.DataFrame, registry_inventory: pd.DataFrame) -> str:
        exams = sorted(master["analysis_exam_id"].dropna().astype(str).unique().tolist()) if not master.empty else []
        recognized_files = int((quality.get("status", pd.Series(dtype=str)) == "OK").sum()) if not quality.empty else 0
        registry_files = int(registry_inventory["file"].nunique()) if not registry_inventory.empty else 0
        note = (
            f"Bu çalıştırmada {recognized_files} EPE kaynak dosyası tanındı; "
            f"{len(exams)} analiz oturumu üretildi ({', '.join(exams) if exams else 'yok'}). "
            f"Ayrıca {registry_files} öğrenci kütüğü envantere alındı."
        )
        if "2023-24_OCAK" not in exams:
            note += (
                " Ocak 2024 orijinal EPE dosyası bulunmadığından bu oturum henüz beceri analizine dahil değildir. "
                "Kütükten türetilen Ocak 2024 adaptörü sonraki kod katmanında aynı analysis_exam_id ile bağlanacaktır."
            )
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
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
