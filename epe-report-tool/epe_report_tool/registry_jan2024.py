from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_january_2024_from_registry(
    path: Path,
    hmac_secret: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Do not create January 2024 exam records from a registry file."""
    _ = hmac_secret
    return pd.DataFrame(), {
        "file": path.name,
        "analysis_exam_id": "2023-24_OCAK",
        "source_session_id": "2023-24_OCAK_REGISTRY_DISABLED",
        "sheet": "—",
        "id_n": 0,
        "expected_id_n": 0,
        "id_n_match": False,
        "result_n": 0,
        "decision_score_n": 0,
        "skill_complete_n": 0,
        "status": "ORIGINAL_EPE_SOURCE_REQUIRED",
        "note": (
            "Ocak 2024 yalnız orijinal EPE dosyası seçildiğinde analize dahil edilir. "
            "Öğrenci kütüğünden EPE sonucu veya karar puanı üretilmez."
        ),
    }
