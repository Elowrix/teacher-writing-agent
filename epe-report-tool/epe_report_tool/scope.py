from __future__ import annotations

import re
import unicodedata

import pandas as pd


def _norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def classify_exclusion(row: pd.Series) -> str | None:
    """Return an exclusion reason only from explicit EPE-source status fields.

    Institutional rule:
    - Registry files may complete faculty, department, scholarship and entry year.
    - Registry faculty/department/status text must never create a MASTER, PHD or
      DISMISSED classification.
    - A record is excluded only when the EPE source itself populated
      ``administrative_status`` or ``student_level`` with an explicit marker.
    """
    administrative = _norm(row.get("administrative_status"))
    level = _norm(row.get("student_level"))

    if (
        "dismissed" in administrative
        or "ilisigi kes" in administrative
        or "ilisik kes" in administrative
    ):
        return "ADMINISTRATIVE_STATUS_DISMISSED"

    master_patterns = (
        r"\bmaster\b",
        r"master'?s",
        r"master program",
        r"graduate candidate",
        r"graduate school",
        r"institute of graduate",
        r"lisansustu programlar enstitusu",
        r"lisansustu",
        r"yuksek lisans",
        r"y\.\s*lisans",
        r"\byl[-_\s]",
        r"\byl\b",
    )
    if any(re.search(pattern, level) for pattern in master_patterns):
        return "STUDENT_LEVEL_MASTER"

    phd_patterns = (
        r"\bphd\b",
        r"doctoral",
        r"doctorate",
        r"doktora",
        r"\bdr[-_\s]",
        r"\bdr\b",
    )
    if any(re.search(pattern, level) for pattern in phd_patterns):
        return "STUDENT_LEVEL_PHD"

    return None


def apply_analysis_scope(master: pd.DataFrame) -> pd.DataFrame:
    """Mark records included in the core undergraduate analysis."""
    if master.empty:
        work = master.copy()
        work["analysis_include"] = pd.Series(dtype="bool")
        work["exclusion_reason"] = pd.Series(dtype="object")
        return work

    work = master.copy()
    work["exclusion_reason"] = work.apply(classify_exclusion, axis=1)
    work["analysis_include"] = work["exclusion_reason"].isna()
    return work


def build_exclusion_table(master: pd.DataFrame) -> pd.DataFrame:
    """Produce an aggregate audit table without exposing student identifiers."""
    if master.empty or "analysis_include" not in master:
        return pd.DataFrame()
    excluded = master[~master["analysis_include"]].copy()
    if excluded.empty:
        return pd.DataFrame(columns=[
            "analysis_exam_id",
            "academic_year",
            "slot",
            "exclusion_reason",
            "N",
            "PASS",
            "FAIL",
            "ABSENT",
        ])

    rows: list[dict[str, object]] = []
    for keys, group in excluded.groupby(
        ["analysis_exam_id", "academic_year", "slot", "exclusion_reason"],
        dropna=False,
    ):
        exam_id, academic_year, slot, reason = keys
        rows.append({
            "analysis_exam_id": exam_id,
            "academic_year": academic_year,
            "slot": slot,
            "exclusion_reason": reason,
            "N": int(len(group)),
            "PASS": int((group["official_result"] == "PASS").sum()),
            "FAIL": int((group["official_result"] == "FAIL").sum()),
            "ABSENT": int((group["official_result"] == "ABSENT").sum()),
        })
    return pd.DataFrame(rows).sort_values(
        ["analysis_exam_id", "exclusion_reason"]
    ).reset_index(drop=True)
