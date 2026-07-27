from __future__ import annotations

import pandas as pd


FINAL_RESULTS = {"PASS", "FAIL"}


def add_cell_size_flag(frame: pd.DataFrame, n_column: str = "N") -> pd.DataFrame:
    """Attach the agreed N-based interpretation category to a result table."""
    if frame.empty:
        return frame.copy()
    work = frame.copy()
    n = pd.to_numeric(work.get(n_column), errors="coerce")
    work["cell_size_flag"] = "N≥10"
    work.loc[n.lt(10), "cell_size_flag"] = "N=5–9: cautious"
    work.loc[n.lt(5), "cell_size_flag"] = "N<5: suppressed"
    work.loc[n.isna(), "cell_size_flag"] = "N unknown"
    return work


def build_participation_table(master: pd.DataFrame) -> pd.DataFrame:
    """Reconcile listed, absent, finalized and unresolved records by exam."""
    if master.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for keys, group in master.groupby(
        ["analysis_exam_id", "academic_year", "slot"], dropna=False
    ):
        exam_id, academic_year, slot = keys
        listed_n = int(len(group))
        pass_n = int((group["official_result"] == "PASS").sum())
        fail_n = int((group["official_result"] == "FAIL").sum())
        absent_n = int((group["official_result"] == "ABSENT").sum())
        finalized_n = pass_n + fail_n
        unresolved_n = listed_n - finalized_n - absent_n
        rows.append({
            "analysis_exam_id": exam_id,
            "academic_year": academic_year,
            "slot": slot,
            "listed_N": listed_n,
            "absent_N": absent_n,
            "finalized_exam_taker_N": finalized_n,
            "PASS": pass_n,
            "FAIL": fail_n,
            "unresolved_or_other_N": unresolved_n,
            "PASS_rate_among_finalized": pass_n / finalized_n if finalized_n else None,
            "absent_rate_among_listed": absent_n / listed_n if listed_n else None,
            "unresolved_rate_among_listed": unresolved_n / listed_n if listed_n else None,
        })
    return pd.DataFrame(rows).sort_values(["slot", "academic_year"]).reset_index(drop=True)


def build_faculty_near_miss_table(master: pd.DataFrame) -> pd.DataFrame:
    """Answer Q5 without mixing the faculty result with scholarship groups."""
    if master.empty:
        return pd.DataFrame()
    valid = master[master["official_result"].isin(FINAL_RESULTS)].copy()
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
    result = pd.DataFrame(rows).sort_values(
        ["analysis_exam_id", "faculty"]
    ).reset_index(drop=True)
    return add_cell_size_flag(result, "FAIL_N")


def build_exam_type_table(master: pd.DataFrame) -> pd.DataFrame:
    """Compare entry and in-term EPEs descriptively using total and skill profiles."""
    if master.empty:
        return pd.DataFrame()
    work = master.copy()
    work["exam_type"] = work["entry_exam"].map(
        {True: "ENTRY", False: "IN_TERM"}
    ).fillna("UNKNOWN")
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


def build_threshold_concentration_table(master: pd.DataFrame) -> pd.DataFrame:
    """Quantify how strongly finalized records concentrate around each threshold."""
    if master.empty:
        return pd.DataFrame()
    valid = master[
        master["official_result"].isin(FINAL_RESULTS)
        & master["distance_to_threshold"].notna()
    ].copy()
    rows: list[dict[str, object]] = []
    for keys, group in valid.groupby(
        ["analysis_exam_id", "academic_year", "slot"], dropna=False
    ):
        exam_id, academic_year, slot = keys
        distance = group["distance_to_threshold"]
        fail = group["official_result"].eq("FAIL")
        passed = group["official_result"].eq("PASS")
        scored_n = int(len(group))
        fail_n = int(fail.sum())
        pass_n = int(passed.sum())
        within_5 = distance.ge(-5) & distance.lt(5)
        within_10 = distance.ge(-10) & distance.lt(10)
        fail_0_5 = fail & distance.ge(-5) & distance.lt(0)
        fail_0_10 = fail & distance.ge(-10) & distance.lt(0)
        pass_0_5 = passed & distance.ge(0) & distance.lt(5)
        pass_0_10 = passed & distance.ge(0) & distance.lt(10)
        rows.append({
            "analysis_exam_id": exam_id,
            "academic_year": academic_year,
            "slot": slot,
            "scored_finalized_N": scored_n,
            "within_5_N": int(within_5.sum()),
            "within_5_rate": float(within_5.mean()) if scored_n else None,
            "within_10_N": int(within_10.sum()),
            "within_10_rate": float(within_10.mean()) if scored_n else None,
            "FAIL_N": fail_n,
            "FAIL_0_5_N": int(fail_0_5.sum()),
            "FAIL_0_5_rate": int(fail_0_5.sum()) / fail_n if fail_n else None,
            "FAIL_0_10_N": int(fail_0_10.sum()),
            "FAIL_0_10_rate": int(fail_0_10.sum()) / fail_n if fail_n else None,
            "PASS_N": pass_n,
            "PASS_0_5_N": int(pass_0_5.sum()),
            "PASS_0_5_rate": int(pass_0_5.sum()) / pass_n if pass_n else None,
            "PASS_0_10_N": int(pass_0_10.sum()),
            "PASS_0_10_rate": int(pass_0_10.sum()) / pass_n if pass_n else None,
        })
    return pd.DataFrame(rows).sort_values(["slot", "academic_year"]).reset_index(drop=True)


def build_near_miss_limitations(
    master: pd.DataFrame,
    near_table: pd.DataFrame,
) -> pd.DataFrame:
    """Flag structurally empty near-miss regions that require cautious interpretation."""
    if master.empty or near_table.empty:
        return pd.DataFrame()
    metadata = master[["analysis_exam_id", "slot", "entry_exam"]].drop_duplicates(
        "analysis_exam_id"
    )
    work = near_table.merge(metadata, on="analysis_exam_id", how="left")
    rows: list[dict[str, object]] = []
    for _, row in work.iterrows():
        zero_near = int(row.get("near_miss_N", 0)) == 0
        substantial_borderline = int(row.get("borderline_pass_N", 0)) > 0
        september = str(row.get("slot")) == "EYLUL"
        if september and zero_near and substantial_borderline:
            rows.append({
                "analysis_exam_id": row["analysis_exam_id"],
                "limitation_code": "BORDERLINE_PROCESS_LIMITATION",
                "severity": "CAUTION",
                "note": (
                    "Eşik altındaki 0–5 puan bandı boş, buna karşılık eşik üstünde "
                    "yığılma vardır. Borderline inceleme veya puan revizyonu nedeniyle "
                    "near-miss oranı doğal puan dağılımını doğrudan temsil etmeyebilir."
                ),
            })
    return pd.DataFrame(rows)


def build_quality_issue_table(
    source_quality: pd.DataFrame,
    registry_match: pd.DataFrame,
    registry_read: pd.DataFrame,
) -> pd.DataFrame:
    """Turn technical quality tables into an explicit review list."""
    issues: list[dict[str, object]] = []

    if not source_quality.empty:
        for _, row in source_quality.iterrows():
            status = str(row.get("status", ""))
            file_name = row.get("file", "—")
            exam_id = row.get("analysis_exam_id", "—")
            if status in {"ERROR", "REGISTRY_ADAPTER_ERROR"}:
                issues.append({
                    "severity": "ERROR",
                    "area": "SOURCE",
                    "file_or_exam": file_name,
                    "issue": status,
                    "impact": str(row.get("note", "Kaynak okunamadı.")),
                })
            elif status == "UNRECOGNIZED":
                issues.append({
                    "severity": "REVIEW",
                    "area": "SOURCE",
                    "file_or_exam": file_name,
                    "issue": "Dosya tanınmadı",
                    "impact": "Kapsama bilerek dahil edilmediyse açıklanmalı; aksi halde sonuçlar eksik olabilir.",
                })

            id_match = row.get("id_n_match")
            if id_match is False or str(id_match).casefold() == "false":
                issues.append({
                    "severity": "REVIEW",
                    "area": "SOURCE",
                    "file_or_exam": exam_id,
                    "issue": "Beklenen ve bulunan N farklı",
                    "impact": f"Bulunan={row.get('id_n', '—')}; beklenen={row.get('expected_id_n', '—')}.",
                })

            id_n = pd.to_numeric(pd.Series([row.get("id_n")]), errors="coerce").iloc[0]
            result_n = pd.to_numeric(pd.Series([row.get("result_n")]), errors="coerce").iloc[0]
            if pd.notna(id_n) and pd.notna(result_n) and result_n < id_n:
                issues.append({
                    "severity": "INFO",
                    "area": "RESULT COVERAGE",
                    "file_or_exam": exam_id,
                    "issue": "Her listelenen kayıtta finalized PASS/FAIL yok",
                    "impact": f"ID N={int(id_n)}; PASS/FAIL N={int(result_n)}; fark={int(id_n-result_n)}.",
                })

    if not registry_match.empty:
        for _, row in registry_match.iterrows():
            unknown_n = int(row.get("faculty_unknown_N", 0) or 0)
            total_n = int(row.get("N", 0) or 0)
            if unknown_n > 0:
                issues.append({
                    "severity": "REVIEW" if unknown_n >= 5 else "INFO",
                    "area": "REGISTRY MATCH",
                    "file_or_exam": row.get("analysis_exam_id", "—"),
                    "issue": "Fakültesi hâlâ bilinmeyen kayıt",
                    "impact": f"Unknown N={unknown_n}/{total_n}; fakülte kırılımları bu kapsamla okunmalı.",
                })

    if not registry_read.empty:
        for _, row in registry_read.iterrows():
            if str(row.get("status", "")) != "OK":
                issues.append({
                    "severity": "ERROR",
                    "area": "REGISTRY READ",
                    "file_or_exam": row.get("file", "—"),
                    "issue": str(row.get("status", "Kütük okuma hatası")),
                    "impact": str(row.get("note", "")),
                })

    columns = ["severity", "area", "file_or_exam", "issue", "impact"]
    return pd.DataFrame(issues, columns=columns)


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
        ("Q12", "Öğrenciler eşik çevresinde mi yoğunlaşıyor?", "Esik Yogunlugu"),
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
