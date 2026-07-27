from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .analytics import (
    clean_student_id,
    normalize_faculty,
    normalize_scholarship,
    normalize_text,
    student_hash,
)
from .config import REGISTRY_SHEETS


CANONICAL_FACULTIES = {
    "Engineering",
    "Education",
    "Arts and Sciences",
    "Architecture and Design",
    "Economics and Administrative Sciences",
}

# Institutional rule: registry files are descriptive enrichment sources only.
# They must never create or overwrite official result, decision score,
# administrative status, student level, or exclusion decisions.
REGISTRY_ENRICHMENT_FIELDS = (
    "faculty",
    "department",
    "scholarship",
    "entry_year",
)


def _detect_academic_year(path: Path) -> str | None:
    text = normalize_text(path.stem).replace("_", " ").replace("-", " ")
    for academic_year in ("2023-2024", "2024-2025", "2025-2026"):
        left, right = academic_year.split("-")
        if left in text and right in text:
            return academic_year
    return None


def _choose_sheet(path: Path, academic_year: str) -> str:
    workbook = pd.ExcelFile(path)
    normalized = {normalize_text(sheet): sheet for sheet in workbook.sheet_names}
    for candidate in REGISTRY_SHEETS.get(academic_year, ()):
        key = normalize_text(candidate)
        if key in normalized:
            return normalized[key]
    return workbook.sheet_names[0]


def _find_header_row(path: Path, sheet: str) -> int:
    preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=15)
    header_tokens = (
        "student id", "student number", "ogrenci numarasi", "öğrenci numarası",
        "faculty", "fakulte", "fakülte", "department", "program",
    )
    best_row = 0
    best_score = -1
    for row_index, row in preview.iterrows():
        values = [normalize_text(value) for value in row.tolist()]
        score = sum(
            1
            for value in values
            if any(token == value or token in value for token in header_tokens)
        )
        if score > best_score:
            best_row = int(row_index)
            best_score = score
    return best_row


def _column_groups(columns: Iterable[object]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "student_id": [],
        "faculty": [],
        "department": [],
        "scholarship": [],
        "entry_year": [],
    }
    for column in columns:
        original = str(column)
        norm = normalize_text(column)
        if not norm or norm.startswith("unnamed"):
            continue

        if norm in {
            "id", "student id", "student no", "student number", "id no",
            "ogrenci numarasi", "öğrenci numarası", "tc",
        }:
            groups["student_id"].append(original)
        elif "student id" in norm or "student number" in norm or "ogrenci numara" in norm:
            groups["student_id"].append(original)

        if norm in {"faculty", "fakulte", "fakülte"} or norm.endswith(" faculty"):
            groups["faculty"].append(original)
        if norm in {"department", "program", "bolum", "bölüm"}:
            groups["department"].append(original)
        if norm in {
            "scholarship", "scholarship rate", "burs", "burs orani", "burs oranı",
        }:
            groups["scholarship"].append(original)
        if norm in {"entry year", "entrance year", "giris yili", "giriş yılı"}:
            groups["entry_year"].append(original)
    return groups


def _first_nonempty(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column)
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if not text or text.casefold() in {"nan", "none", "#n/a"}:
            continue
        return value
    return pd.NA


def _canonical_faculty(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column)
        if value is None or pd.isna(value):
            continue
        normalized = normalize_faculty(value)
        if normalized in CANONICAL_FACULTIES:
            return normalized
    return pd.NA


def _completeness(record: dict[str, object]) -> int:
    return sum(
        value is not None
        and not pd.isna(value)
        and str(value).strip() not in {"", "#N/A"}
        for key, value in record.items()
        if key not in {"academic_year", "student_hash"}
    )


def build_registry_lookup(
    paths: Iterable[Path],
    hmac_secret: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup: dict[tuple[str, str], dict[str, object]] = {}
    audit_rows: list[dict[str, object]] = []

    for path in paths:
        academic_year = _detect_academic_year(path)
        if academic_year is None:
            audit_rows.append({
                "file": path.name,
                "academic_year": "UNKNOWN",
                "status": "YEAR_NOT_RECOGNIZED",
                "sheet": "—",
                "source_rows": 0,
                "lookup_id_n": 0,
                "conflict_n": 0,
                "note": "Dosya adından akademik yıl belirlenemedi.",
            })
            continue

        try:
            sheet = _choose_sheet(path, academic_year)
            header_row = _find_header_row(path, sheet)
            frame = pd.read_excel(path, sheet_name=sheet, header=header_row)
            frame.columns = [str(column).strip() for column in frame.columns]
            groups = _column_groups(frame.columns)
            if not groups["student_id"]:
                raise ValueError("Öğrenci numarası sütunu bulunamadı")

            file_keys: set[tuple[str, str]] = set()
            conflict_n = 0
            for _, row in frame.iterrows():
                candidate_ids: set[str] = set()
                for column in groups["student_id"]:
                    cleaned = clean_student_id(row.get(column))
                    if cleaned:
                        candidate_ids.add(cleaned)
                if not candidate_ids:
                    continue

                record = {
                    "academic_year": academic_year,
                    "faculty_registry": _canonical_faculty(row, groups["faculty"]),
                    "department_registry": _first_nonempty(row, groups["department"]),
                    "scholarship_registry": normalize_scholarship(
                        _first_nonempty(row, groups["scholarship"])
                    ),
                    "entry_year_registry": _first_nonempty(row, groups["entry_year"]),
                    "registry_source_file": path.name,
                    "registry_source_sheet": sheet,
                }

                for candidate_id in candidate_ids:
                    hashed = student_hash(candidate_id, hmac_secret)
                    key = (academic_year, hashed)
                    candidate_record = {**record, "student_hash": hashed}
                    current = lookup.get(key)
                    if current is None:
                        lookup[key] = candidate_record
                    elif _completeness(candidate_record) > _completeness(current):
                        lookup[key] = candidate_record
                        conflict_n += 1
                    elif candidate_record != current:
                        conflict_n += 1
                    file_keys.add(key)

            audit_rows.append({
                "file": path.name,
                "academic_year": academic_year,
                "status": "OK",
                "sheet": sheet,
                "header_row_zero_based": header_row,
                "source_rows": int(len(frame)),
                "id_columns": " | ".join(groups["student_id"]),
                "faculty_columns": " | ".join(groups["faculty"]),
                "department_columns": " | ".join(groups["department"]),
                "lookup_id_n": int(len(file_keys)),
                "conflict_n": int(conflict_n),
                "note": (
                    "Kütük yalnız fakülte, bölüm, burs ve giriş yılı alanlarını "
                    "öğrenci numarası HMAC özeti üzerinden tamamlar; öğrenci düzeyi "
                    "ve idari statü kütükten alınmaz."
                ),
            })
        except Exception as exc:  # noqa: BLE001
            audit_rows.append({
                "file": path.name,
                "academic_year": academic_year,
                "status": "ERROR",
                "sheet": "—",
                "source_rows": 0,
                "lookup_id_n": 0,
                "conflict_n": 0,
                "note": str(exc),
            })

    lookup_frame = pd.DataFrame(list(lookup.values()))
    if not lookup_frame.empty:
        lookup_frame = lookup_frame.drop_duplicates(
            ["academic_year", "student_hash"], keep="last"
        )
    return lookup_frame, pd.DataFrame(audit_rows)


def _valid_source_faculty(value: object) -> object:
    normalized = normalize_faculty(value)
    return normalized if normalized in CANONICAL_FACULTIES else pd.NA


def enrich_from_registries(
    master: pd.DataFrame,
    registry_files: Iterable[Path],
    hmac_secret: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Complete descriptive fields without changing scope or official status."""
    lookup, registry_audit = build_registry_lookup(registry_files, hmac_secret)
    if master.empty:
        return master.copy(), registry_audit, pd.DataFrame()

    work = master.copy()
    work["faculty"] = work["faculty"].map(_valid_source_faculty)
    if lookup.empty:
        work["registry_match"] = False
        return work, registry_audit, _match_audit(work)

    work = work.merge(
        lookup,
        how="left",
        on=["academic_year", "student_hash"],
        validate="many_to_one",
    )
    work["registry_match"] = work["registry_source_file"].notna()

    work["faculty"] = work["faculty_registry"].combine_first(work["faculty"])
    work["department"] = work["department_registry"].combine_first(work["department"])
    work["scholarship"] = work["scholarship_registry"].combine_first(work["scholarship"])
    work["entry_year"] = work["entry_year_registry"].combine_first(work["entry_year"])

    drop_columns = [
        "faculty_registry",
        "department_registry",
        "scholarship_registry",
        "entry_year_registry",
    ]
    work.drop(
        columns=[column for column in drop_columns if column in work],
        inplace=True,
    )
    return work, registry_audit, _match_audit(work)


def _match_audit(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for exam_id, group in master.groupby("analysis_exam_id", dropna=False):
        n = int(len(group))
        matched = int(
            group.get("registry_match", pd.Series(False, index=group.index))
            .fillna(False)
            .sum()
        )
        faculty_known = int(group["faculty"].isin(CANONICAL_FACULTIES).sum())
        department_known = int(group["department"].notna().sum())
        rows.append({
            "analysis_exam_id": exam_id,
            "N": n,
            "registry_match_N": matched,
            "registry_match_rate": matched / n if n else None,
            "faculty_known_N": faculty_known,
            "faculty_unknown_N": n - faculty_known,
            "department_known_N": department_known,
            "status_or_level_from_registry_N": 0,
        })
    return pd.DataFrame(rows).sort_values("analysis_exam_id").reset_index(drop=True)
