from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .analytics import (
    clean_student_id,
    normalize_faculty,
    normalize_result,
    normalize_scholarship,
    normalize_text,
    numeric,
    student_hash,
)


ALIASES: dict[str, tuple[str, ...]] = {
    "student_id": ("student id", "student no", "student number", "ogrenci no", "öğrenci no", "id no"),
    "fall_epe_total": ("fall epe total", "fall epe grade", "fall epe score", "fall epe", "ocak epe", "january epe"),
    "fall_epe_result": ("fall epe pass/fail", "fall epe result", "fall epe status", "ocak epe result", "january epe result"),
    "module_2_grade": ("module 2 grade", "module 2 total", "modul 2 grade", "modül 2 grade", "m2 grade", "course grade"),
    "module_2_level": ("module 2 level", "modul 2 level", "modül 2 level", "m2 level", "level"),
    "faculty": ("faculty", "fakulte", "fakülte"),
    "department": ("department", "program", "bolum", "bölüm"),
    "scholarship": ("scholarship rate", "scholarship", "burs orani", "burs oranı", "burs"),
    "entry_year": ("entry year", "entrance year", "giris yili", "giriş yılı"),
}


def _find_header_row(path: Path, sheet: str) -> int:
    preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=20)
    best_row = 0
    best_score = -1
    alias_values = [normalize_text(alias) for aliases in ALIASES.values() for alias in aliases]
    for row_index, row in preview.iterrows():
        values = [normalize_text(value) for value in row.tolist()]
        score = sum(1 for value in values if any(alias == value or alias in value for alias in alias_values))
        if score > best_score:
            best_score = score
            best_row = int(row_index)
    return best_row


def _choose_sheet(path: Path) -> str:
    workbook = pd.ExcelFile(path)
    preferred = [sheet for sheet in workbook.sheet_names if normalize_text(sheet) == "2023-2024"]
    return preferred[0] if preferred else workbook.sheet_names[0]


def _map_columns(columns: Iterable[object]) -> dict[str, str]:
    normalized = {normalize_text(column): str(column) for column in columns if normalize_text(column)}
    mapping: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            key = normalize_text(alias)
            if key in normalized:
                mapping[field] = normalized[key]
                break
        if field in mapping:
            continue
        candidates: list[str] = []
        for norm, original in normalized.items():
            for alias in aliases:
                key = normalize_text(alias)
                if key and (key in norm or norm in key):
                    candidates.append(original)
                    break
        if len(set(candidates)) == 1:
            mapping[field] = candidates[0]
    return mapping


def _kur_type(value: object) -> str | None:
    text = normalize_text(value).upper()
    if not text:
        return None
    if "SUCCESS" in text or "ENG085" in text:
        return "SUCCESS"
    if "EXT" in text:
        return "EXTENDED"
    if "SHORT" in text or "UPPER" in text:
        return "SHORT"
    return text


def load_january_2024_from_registry(path: Path, hmac_secret: str) -> tuple[pd.DataFrame, dict[str, object]]:
    sheet = _choose_sheet(path)
    header_row = _find_header_row(path, sheet)
    frame = pd.read_excel(path, sheet_name=sheet, header=header_row)
    frame.columns = [str(column).strip() for column in frame.columns]
    mapping = _map_columns(frame.columns)

    required = {"student_id", "fall_epe_result", "fall_epe_total", "module_2_level"}
    missing = sorted(required - set(mapping))
    if missing:
        return pd.DataFrame(), {
            "file": path.name,
            "analysis_exam_id": "2023-24_OCAK",
            "source_session_id": "2023-24_OCAK_REGISTRY",
            "sheet": sheet,
            "status": "REGISTRY_COLUMNS_MISSING",
            "note": f"Eksik alanlar: {', '.join(missing)}; bulunan eşleme: {mapping}",
        }

    out = pd.DataFrame(index=frame.index)
    for field in ALIASES:
        source = mapping.get(field)
        out[field] = frame[source] if source else pd.NA

    out["student_id"] = out["student_id"].map(clean_student_id)
    out = out[out["student_id"].notna()].copy()
    out["official_result"] = out["fall_epe_result"].map(normalize_result)
    out = out[out["official_result"].isin(["PASS", "FAIL"])].copy()
    out["epe_total"] = numeric(out["fall_epe_total"])
    out["course_grade"] = numeric(out["module_2_grade"])
    out["kur_code_raw"] = out["module_2_level"]
    out["kur_type"] = out["module_2_level"].map(_kur_type)

    is_success = out["kur_type"].eq("SUCCESS")
    out["decision_score"] = pd.NA
    out.loc[is_success, "decision_score"] = out.loc[is_success, "epe_total"]
    weighted = ~is_success & out["epe_total"].notna() & out["course_grade"].notna()
    out.loc[weighted, "decision_score"] = (
        out.loc[weighted, "epe_total"] * 0.60 + out.loc[weighted, "course_grade"] * 0.40
    )
    out["decision_score"] = pd.to_numeric(out["decision_score"], errors="coerce")

    out["faculty"] = out["faculty"].map(normalize_faculty)
    out["scholarship"] = out["scholarship"].map(normalize_scholarship)
    out["student_hash"] = out["student_id"].map(lambda value: student_hash(str(value), hmac_secret))
    out.drop(columns=["student_id", "fall_epe_result", "fall_epe_total", "module_2_grade", "module_2_level"], inplace=True)

    for field in ("booklet", "writing", "speaking", "att_booklet", "att_writing", "att_speaking", "administrative_status", "student_level", "prep_year_group"):
        out[field] = pd.NA
    out["analysis_exam_id"] = "2023-24_OCAK"
    out["source_session_id"] = "2023-24_OCAK_REGISTRY"
    out["academic_year"] = "2023-2024"
    out["slot"] = "OCAK"
    out["sitting_order"] = 1
    out["source_file"] = path.name
    out["source_sheet"] = sheet
    out["entry_exam"] = False

    quality = {
        "file": path.name,
        "analysis_exam_id": "2023-24_OCAK",
        "source_session_id": "2023-24_OCAK_REGISTRY",
        "sheet": sheet,
        "id_n": int(len(out)),
        "expected_id_n": 389,
        "id_n_match": int(len(out)) == 389,
        "result_n": int(out["official_result"].isin(["PASS", "FAIL"]).sum()),
        "decision_score_n": int(out["decision_score"].notna().sum()),
        "skill_complete_n": 0,
        "status": "PARTIAL_DERIVED",
        "note": "Ocak 2024 karar puanı kütükten türetilmiştir; resmî PASS/FAIL değiştirilmez; beceri alanları yoktur.",
    }
    return out, quality
