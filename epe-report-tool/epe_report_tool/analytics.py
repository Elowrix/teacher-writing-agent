from __future__ import annotations

import hashlib
import hmac
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import (
    ELL_ELT_KEYWORDS,
    ELL_ELT_THRESHOLD,
    FINAL_RESULT_VALUES,
    OTHER_UG_THRESHOLD,
    ROUNDING_TOLERANCE,
    SESSIONS,
    SessionConfig,
)


CANONICAL_FIELDS = (
    "student_id", "official_result", "decision_score", "epe_total", "booklet", "writing",
    "speaking", "course_grade", "faculty", "department", "entry_year", "scholarship",
    "kur_code_raw", "administrative_status", "student_level", "att_booklet", "att_writing",
    "att_speaking", "prep_year_group",
)


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip().replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def normalize_filename(path: Path) -> str:
    text = normalize_text(path.stem)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def clean_student_id(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text or text.casefold() in {"nan", "none"}:
        return None
    text = re.sub(r"\s+", "", text).upper()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text or None


def student_hash(student_id: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), student_id.encode("utf-8"), hashlib.sha256).hexdigest()


def numeric(series: pd.Series) -> pd.Series:
    if series.empty:
        return pd.Series(dtype="float64")
    cleaned = series.astype(str).str.replace(",", ".", regex=False)
    cleaned = cleaned.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_result(value: object) -> str | None:
    text = normalize_text(value).upper()
    if not text:
        return None
    if "ABSENT" in text or text in {"ZX", "FX"}:
        return "ABSENT"
    if "PASS" in text and "FAIL" not in text:
        return "PASS"
    if "FAIL" in text:
        return "FAIL"
    return None


def normalize_scholarship(value: object) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    if any(token in text for token in ("burssuz", "no scholarship", "%0")):
        return 0.0
    match = re.search(r"(?:%\s*)?(100|75|50|25|0)(?:\s*%)?", text)
    if match:
        return float(match.group(1))
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return None
    if 0 <= number <= 1:
        return number * 100
    if number in {0, 25, 50, 75, 100}:
        return number
    return None


def normalize_faculty(value: object) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    mapping = (
        (("engineering", "muhendislik"), "Engineering"),
        (("education", "egitim"), "Education"),
        (("arts and sciences", "fen edebiyat", "fen-edebiyat"), "Arts and Sciences"),
        (("architecture", "mimarlik", "design", "tasarim"), "Architecture and Design"),
        (("economics", "administrative sciences", "iktisadi", "idari bilimler"), "Economics and Administrative Sciences"),
    )
    for tokens, label in mapping:
        if any(token in text for token in tokens):
            return label
    return str(value).strip()


def threshold_group(department: object, faculty: object = None) -> str:
    text = f"{normalize_text(department)} {normalize_text(faculty)}"
    return "ELL–ELT" if any(keyword in text for keyword in ELL_ELT_KEYWORDS) else "Other undergraduate"


def decision_threshold(group: str) -> float:
    return ELL_ELT_THRESHOLD if group == "ELL–ELT" else OTHER_UG_THRESHOLD


def score_band(distance: float | None, result: str | None) -> str | None:
    if distance is None or pd.isna(distance) or result not in FINAL_RESULT_VALUES:
        return None
    d = float(distance)
    if result == "PASS":
        if 0 <= d < 5: return "PASS 0–5"
        if 5 <= d < 10: return "PASS 5–10"
        if 10 <= d < 15: return "PASS 10–15"
        if 15 <= d < 20: return "PASS 15–20"
        if d >= 20: return "PASS 20+"
        return "PASS below threshold"
    below = -d
    if 0 < below <= 5: return "FAIL 0–5"
    if 5 < below <= 10: return "FAIL 5–10"
    if 10 < below <= 15: return "FAIL 10–15"
    if 15 < below <= 20: return "FAIL 15–20"
    if 20 < below <= 30: return "FAIL 20–30"
    if below > 30: return "FAIL 30+"
    return "FAIL at/above threshold"


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


@dataclass
class SessionLoad:
    config: SessionConfig
    frame: pd.DataFrame
    quality: dict[str, object]


class EPEAnalyzer:
    def __init__(self, hmac_secret: str) -> None:
        self.hmac_secret = hmac_secret

    def identify_session(self, path: Path) -> SessionConfig | None:
        name = normalize_filename(path)
        scored: list[tuple[int, SessionConfig]] = []
        for config in SESSIONS:
            score = sum(1 for token in config.file_tokens if normalize_text(token) in name)
            if score:
                scored.append((score, config))
        if not scored:
            return None
        return max(scored, key=lambda item: item[0])[1]

    def load_files(self, paths: Iterable[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
        loads: list[SessionLoad] = []
        quality_rows: list[dict[str, object]] = []
        for path in paths:
            config = self.identify_session(path)
            if config is None:
                quality_rows.append({"file": path.name, "status": "UNRECOGNIZED", "note": "Dosya adı oturumla eşleşmedi"})
                continue
            try:
                loaded = self._load_session(path, config)
                loads.append(loaded)
                quality_rows.append(loaded.quality)
            except Exception as exc:  # noqa: BLE001
                quality_rows.append({"file": path.name, "analysis_exam_id": config.analysis_exam_id, "status": "ERROR", "note": str(exc)})

        if not loads:
            return pd.DataFrame(), pd.DataFrame(quality_rows)

        combined = pd.concat([item.frame for item in loads], ignore_index=True, sort=False)
        combined = self._apply_last_sitting_rule(combined)
        combined = self._derive_fields(combined)
        return combined, pd.DataFrame(quality_rows)

    def _select_sheet(self, path: Path, config: SessionConfig) -> str:
        workbook = pd.ExcelFile(path)
        normalized = {normalize_text(sheet): sheet for sheet in workbook.sheet_names}
        for candidate in config.sheet_candidates:
            key = normalize_text(candidate)
            if key in normalized:
                return normalized[key]
        for candidate in config.sheet_candidates:
            key = normalize_text(candidate)
            for norm, original in normalized.items():
                if key in norm or norm in key:
                    return original
        raise ValueError(f"Beklenen sayfa bulunamadı: {config.sheet_candidates}; mevcut={workbook.sheet_names}")

    def _find_columns(self, columns: Iterable[object], config: SessionConfig) -> dict[str, str]:
        norm_to_original: dict[str, str] = {}
        for column in columns:
            norm = normalize_text(column)
            if norm and not norm.startswith("unnamed"):
                norm_to_original.setdefault(norm, str(column))
        result: dict[str, str] = {}
        for field in CANONICAL_FIELDS:
            for alias in config.columns.get(field, ()): 
                key = normalize_text(alias)
                if key in norm_to_original:
                    result[field] = norm_to_original[key]
                    break
            if field in result:
                continue
            for alias in config.columns.get(field, ()):
                key = normalize_text(alias)
                candidates = [original for norm, original in norm_to_original.items() if key and (key in norm or norm in key)]
                if len(candidates) == 1:
                    result[field] = candidates[0]
                    break
        return result

    def _load_session(self, path: Path, config: SessionConfig) -> SessionLoad:
        sheet = self._select_sheet(path, config)
        frame = pd.read_excel(path, sheet_name=sheet, header=config.header_row)
        frame.columns = [str(col).strip() for col in frame.columns]
        mapping = self._find_columns(frame.columns, config)
        if "student_id" not in mapping:
            raise ValueError(f"Öğrenci ID sütunu bulunamadı; sütunlar={list(frame.columns)}")

        out = pd.DataFrame(index=frame.index)
        for field in CANONICAL_FIELDS:
            source = mapping.get(field)
            out[field] = frame[source] if source else pd.NA

        out["student_id"] = out["student_id"].map(clean_student_id)
        out = out[out["student_id"].notna()].copy()
        out["student_hash"] = out["student_id"].map(lambda value: student_hash(str(value), self.hmac_secret))
        out.drop(columns=["student_id"], inplace=True)
        out["official_result"] = out["official_result"].map(normalize_result)
        for field in ("decision_score", "epe_total", "booklet", "writing", "speaking", "course_grade"):
            out[field] = numeric(out[field])
        out["scholarship"] = out["scholarship"].map(normalize_scholarship)
        out["faculty"] = out["faculty"].map(normalize_faculty)
        out["analysis_exam_id"] = config.analysis_exam_id
        out["source_session_id"] = config.source_session_id
        out["academic_year"] = config.academic_year
        out["slot"] = config.slot
        out["sitting_order"] = config.sitting_order
        out["source_file"] = path.name
        out["source_sheet"] = sheet
        out["entry_exam"] = config.entry_exam

        quality = {
            "file": path.name,
            "analysis_exam_id": config.analysis_exam_id,
            "source_session_id": config.source_session_id,
            "sheet": sheet,
            "id_n": int(len(out)),
            "expected_id_n": config.expected_id_n,
            "id_n_match": config.expected_id_n is None or int(len(out)) == config.expected_id_n,
            "result_n": int(out["official_result"].isin(FINAL_RESULT_VALUES).sum()),
            "decision_score_n": int(out["decision_score"].notna().sum()),
            "skill_complete_n": int(out[["booklet", "writing", "speaking"]].notna().all(axis=1).sum()),
            "status": "OK",
            "note": config.notes,
        }
        return SessionLoad(config=config, frame=out, quality=quality)

    @staticmethod
    def _apply_last_sitting_rule(frame: pd.DataFrame) -> pd.DataFrame:
        ordered = frame.sort_values(["analysis_exam_id", "student_hash", "sitting_order"])
        return ordered.drop_duplicates(["analysis_exam_id", "student_hash"], keep="last").reset_index(drop=True)

    @staticmethod
    def _derive_fields(frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()
        frame["threshold_group"] = [threshold_group(d, f) for d, f in zip(frame["department"], frame["faculty"])]
        frame["threshold"] = frame["threshold_group"].map(decision_threshold)
        frame["distance_to_threshold"] = frame["decision_score"] - frame["threshold"]
        frame["band"] = [score_band(d, r) for d, r in zip(frame["distance_to_threshold"], frame["official_result"])]
        frame["near_miss"] = (frame["official_result"] == "FAIL") & frame["distance_to_threshold"].ge(-5) & frame["distance_to_threshold"].lt(0)
        frame["borderline_pass"] = (frame["official_result"] == "PASS") & frame["distance_to_threshold"].ge(0) & frame["distance_to_threshold"].lt(5)
        frame["productive"] = frame["writing"] + frame["speaking"]
        frame["receptive_pct"] = frame["booklet"] / 50 * 100
        frame["productive_pct"] = frame["productive"] / 50 * 100
        frame["writing_pct"] = frame["writing"] / 25 * 100
        frame["speaking_pct"] = frame["speaking"] / 25 * 100
        frame["productive_minus_receptive"] = frame["productive_pct"] - frame["receptive_pct"]
        frame["writing_minus_speaking"] = frame["writing_pct"] - frame["speaking_pct"]
        frame["result_threshold_validation"] = "NOT_CHECKED"
        valid = frame["decision_score"].notna() & frame["official_result"].isin(FINAL_RESULT_VALUES)
        predicted = frame["decision_score"] >= frame["threshold"]
        matched = valid & (((frame["official_result"] == "PASS") & predicted) | ((frame["official_result"] == "FAIL") & ~predicted))
        tolerance = valid & ~matched & (frame["distance_to_threshold"].abs() <= ROUNDING_TOLERANCE)
        frame.loc[matched, "result_threshold_validation"] = "MATCH"
        frame.loc[tolerance, "result_threshold_validation"] = "ROUNDING_TOLERANCE"
        frame.loc[valid & ~matched & ~tolerance, "result_threshold_validation"] = "MISMATCH"
        frame.loc[frame["decision_score"].isna(), "result_threshold_validation"] = "MISSING_DECISION_SCORE"
        return frame


def build_result_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    valid = master[master["official_result"].isin(FINAL_RESULT_VALUES)].copy()
    rows: list[dict[str, object]] = []
    for keys, group in valid.groupby(["analysis_exam_id", "academic_year", "slot"], dropna=False):
        analysis_exam_id, academic_year, slot = keys
        n = len(group)
        pass_n = int((group["official_result"] == "PASS").sum())
        fail_n = int((group["official_result"] == "FAIL").sum())
        lower, upper = wilson_interval(pass_n, n)
        rows.append({
            "analysis_exam_id": analysis_exam_id, "academic_year": academic_year, "slot": slot,
            "N": n, "PASS": pass_n, "FAIL": fail_n, "PASS_rate": pass_n / n if n else None,
            "Wilson_lower": lower, "Wilson_upper": upper,
        })
    return pd.DataFrame(rows).sort_values(["slot", "academic_year"]).reset_index(drop=True)


def build_near_miss_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for exam_id, group in master.groupby("analysis_exam_id", dropna=False):
        fail = group[group["official_result"] == "FAIL"]
        passed = group[group["official_result"] == "PASS"]
        near = int(fail["near_miss"].sum())
        borderline = int(passed["borderline_pass"].sum())
        rows.append({
            "analysis_exam_id": exam_id,
            "FAIL_N": len(fail), "near_miss_N": near,
            "near_miss_rate_among_FAIL": near / len(fail) if len(fail) else None,
            "PASS_N": len(passed), "borderline_pass_N": borderline,
            "borderline_rate_among_PASS": borderline / len(passed) if len(passed) else None,
        })
    return pd.DataFrame(rows).sort_values("analysis_exam_id").reset_index(drop=True)


def build_band_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    return (
        master[master["band"].notna()]
        .groupby(["analysis_exam_id", "band"], dropna=False)
        .size().reset_index(name="N")
        .sort_values(["analysis_exam_id", "band"])
        .reset_index(drop=True)
    )


def build_threshold_group_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    valid = master[master["official_result"].isin(FINAL_RESULT_VALUES)]
    rows: list[dict[str, object]] = []
    for keys, group in valid.groupby(["analysis_exam_id", "threshold_group"], dropna=False):
        exam_id, group_name = keys
        n = len(group)
        pass_n = int((group["official_result"] == "PASS").sum())
        lower, upper = wilson_interval(pass_n, n)
        rows.append({"analysis_exam_id": exam_id, "threshold_group": group_name, "N": n, "PASS": pass_n,
                     "FAIL": n - pass_n, "PASS_rate": pass_n / n if n else None,
                     "Wilson_lower": lower, "Wilson_upper": upper})
    return pd.DataFrame(rows)


def build_faculty_scholarship_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    valid = master[master["official_result"].isin(FINAL_RESULT_VALUES)].copy()
    valid["faculty"] = valid["faculty"].fillna("Unknown")
    valid["scholarship"] = valid["scholarship"].fillna(-1)
    rows: list[dict[str, object]] = []
    for keys, group in valid.groupby(["analysis_exam_id", "faculty", "scholarship"], dropna=False):
        exam_id, faculty, scholarship = keys
        n = len(group)
        pass_n = int((group["official_result"] == "PASS").sum())
        fail_n = n - pass_n
        near_n = int(group["near_miss"].sum())
        rows.append({"analysis_exam_id": exam_id, "faculty": faculty,
                     "scholarship": None if scholarship == -1 else scholarship,
                     "N": n, "PASS": pass_n, "FAIL": fail_n,
                     "PASS_rate": pass_n / n if n else None,
                     "near_miss_N": near_n,
                     "near_miss_rate_among_FAIL": near_n / fail_n if fail_n else None})
    return pd.DataFrame(rows)


def build_skill_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    complete = master[["booklet", "writing", "speaking"]].notna().all(axis=1)
    skill = master[complete].copy()
    if skill.empty:
        return pd.DataFrame()
    skill["threshold_side"] = pd.NA
    skill.loc[skill["distance_to_threshold"].ge(-5) & skill["distance_to_threshold"].lt(0), "threshold_side"] = "0–5 below"
    skill.loc[skill["distance_to_threshold"].ge(0) & skill["distance_to_threshold"].lt(5), "threshold_side"] = "0–5 above"
    skill = skill[skill["threshold_side"].notna()]
    return (
        skill.groupby(["analysis_exam_id", "threshold_side"], dropna=False)
        .agg(N=("student_hash", "size"), receptive_pct=("receptive_pct", "mean"),
             productive_pct=("productive_pct", "mean"), writing_pct=("writing_pct", "mean"),
             speaking_pct=("speaking_pct", "mean"),
             productive_minus_receptive=("productive_minus_receptive", "mean"),
             writing_minus_speaking=("writing_minus_speaking", "mean"))
        .reset_index()
    )


def build_validation_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    return (
        master.groupby(["analysis_exam_id", "result_threshold_validation"], dropna=False)
        .size().reset_index(name="N")
        .sort_values(["analysis_exam_id", "result_threshold_validation"])
        .reset_index(drop=True)
    )
