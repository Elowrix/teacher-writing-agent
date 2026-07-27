from __future__ import annotations

import pandas as pd


def build_faculty_near_miss_table(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        return pd.DataFrame()
    valid = master[master["official_result"].isin(["PASS", "FAIL"])].copy()
    valid["faculty"] = valid["faculty"].fillna("Unknown")
    rows: list[dict[str, object]] = []
    for keys, group in valid.groupby(["analysis_exam_id", "faculty"], dropna=False):
        exam_id, faculty = keys
        fail = group[group["official_result"] == "FAIL"]
        near_n = int(fail["near_miss"].sum()) if not fail.empty else 0
        rows.append({
            "analysis_exam_id": exam_id,
            "faculty": faculty,
            "N": int(len(group)),
            "FAIL_N": int(len(fail)),
            "near_miss_N": near_n,
            "near_miss_rate_among_FAIL": near_n / len(fail) if len(fail) else None,
        })
    return pd.DataFrame(rows).sort_values(["analysis_exam_id", "faculty"]).reset_index(drop=True)


def build_exam_type_table(master: pd.DataFrame) -> pd.DataFrame:
    """Compare entry and in-term EPEs descriptively using EPE total and skill profiles."""
    if master.empty:
        return pd.DataFrame()
    work = master.copy()
    work["exam_type"] = work["entry_exam"].map({True: "ENTRY", False: "IN_TERM"}).fillna("UNKNOWN")
    work["skill_complete"] = work[["booklet", "writing", "speaking"]].notna().all(axis=1)
    work["productive"] = work["writing"] + work["speaking"]
    rows: list[dict[str, object]] = []
    for keys, group in work.groupby(["academic_year", "exam_type"], dropna=False):
        academic_year, exam_type = keys
        epe = group["epe_total"].dropna()
        skills = group[group["skill_complete"]]
        rows.append({
            "academic_year": academic_year,
            "exam_type": exam_type,
            "N": int(len(group)),
            "epe_total_N": int(len(epe)),
            "epe_total_mean": float(epe.mean()) if len(epe) else None,
            "epe_total_median": float(epe.median()) if len(epe) else None,
            "skill_N": int(len(skills)),
            "receptive_pct": float((skills["booklet"] / 50 * 100).mean()) if len(skills) else None,
            "productive_pct": float((skills["productive"] / 50 * 100).mean()) if len(skills) else None,
            "writing_pct": float((skills["writing"] / 25 * 100).mean()) if len(skills) else None,
            "speaking_pct": float((skills["speaking"] / 25 * 100).mean()) if len(skills) else None,
        })
    return pd.DataFrame(rows).sort_values(["academic_year", "exam_type"]).reset_index(drop=True)


def build_question_coverage_table(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks = [
        ("Q1", "PASS/FAIL oranları yıllar içinde nasıl değişti?", "Genel Sonuclar"),
        ("Q2", "Kalanların ne kadarı eşiğin ilk 5 puanı içinde?", "Near Miss"),
        ("Q3", "Geçenlerin ne kadarı sınırda geçti?", "Near Miss"),
        ("Q4", "ELL–ELT ile diğer lisans programları nasıl farklılaşıyor?", "Esik Gruplari"),
        ("Q5", "Near-miss hangi fakültelerde yoğunlaşıyor?", "Fakulte Near Miss"),
        ("Q6", "Burs gruplarının sonuçları fakültelere göre nasıl değişiyor?", "Fakulte Burs"),
        ("Q7", "Aynı fakülte içinde burs grupları nasıl farklılaşıyor?", "Fakulte Burs"),
        ("Q8", "Eşiğin 0–5 puan altı ve üstü beceri profilleri nasıl farklılaşıyor?", "Beceri Profili"),
        ("Q9", "Productive ve receptive göreli görünüm nedir?", "Beceri Profili"),
        ("Q10", "Writing ve Speaking profilleri nasıl farklılaşıyor?", "Beceri Profili"),
        ("Q11", "Giriş ve dönem içi EPE toplam/skill profilleri nasıl farklılaşıyor?", "Sinav Turu"),
        ("Q12", "Öğrenciler eşik çevresinde mi yoğunlaşıyor?", "Bantlar"),
    ]
    rows = []
    for qid, text, table_name in checks:
        frame = tables.get(table_name, pd.DataFrame())
        rows.append({
            "question_id": qid,
            "question": text,
            "source_table": table_name,
            "supported": not frame.empty,
            "row_count": int(len(frame)),
        })
    return pd.DataFrame(rows)
