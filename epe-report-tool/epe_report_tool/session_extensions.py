from __future__ import annotations

from . import config


JANUARY_2024_ORIGINAL = config.SessionConfig(
    source_session_id="2023-24_OCAK_01",
    analysis_exam_id="2023-24_OCAK",
    academic_year="2023-2024",
    slot="OCAK",
    sitting_order=2,
    file_tokens=("2023 2024 epe", "2023_2024_epe", "ocak 2024 epe", "january 2024 epe"),
    sheet_candidates=("Sheet1",),
    header_row=0,
    entry_exam=False,
    expected_id_n=375,
    columns=config.aliases(
        student_id=("öğrenci numarası", "ogrenci numarasi"),
        official_result=("pass/fail",),
        decision_score=("overall epe",),
        epe_total=("epe total",),
        booklet=("reading&listening", "reading & listening"),
        speaking=("speaking",),
        writing=("writing",),
        course_grade=("course grade",),
        faculty=("faculty",),
        department=("department",),
    ),
    notes=(
        "Ocak 2024 orijinal birleşik kaynak. Overall EPE doğrudan karar puanıdır. "
        "Course grade alanındaki 643 kodu SUCCESS kaydını gösterir; karar puanı hesaplamasında kullanılmaz."
    ),
)


def register_session_extensions() -> None:
    """Add optional source definitions once, before the analytics module imports SESSIONS."""
    if any(session.source_session_id == JANUARY_2024_ORIGINAL.source_session_id for session in config.SESSIONS):
        return
    config.SESSIONS = config.SESSIONS + (JANUARY_2024_ORIGINAL,)
