from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionConfig:
    source_session_id: str
    analysis_exam_id: str
    academic_year: str
    slot: str
    sitting_order: int
    file_tokens: tuple[str, ...]
    sheet_candidates: tuple[str, ...]
    header_row: int = 0
    entry_exam: bool = False
    expected_id_n: int | None = None
    columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    notes: str = ""


COMMON_ALIASES: dict[str, tuple[str, ...]] = {
    "student_id": (
        "student id", "student no", "student number", "student id no", "id no",
        "ogrenci no", "öğrenci no", "id", "student number/id",
    ),
    "official_result": (
        "pass/fail", "fail/pass", "result", "exit level pass/fail", "epe fail/pass",
    ),
    "decision_score": (
        "overall grade", "epe passing grade", "exit level grade (prep+epe) success only epe",
        "total grade", "total score", "epe total",
    ),
    "epe_total": (
        "epe total", "epe total score", "total epe score", "total",
    ),
    "booklet": (
        "booklet score", "epe booklet score", "epe booklet", "rd&ls", "rd & ls score",
        "epe r&l", "r&l", "rd&ls score",
    ),
    "writing": (
        "writing", "writing score", "epe writing", "epe writing score", "wr", "w",
        "wr score",
    ),
    "speaking": (
        "speaking", "speaking score", "epe speaking", "epe speaking score", "sp",
        "sp score",
    ),
    "course_grade": (
        "course grade", "course grades", "module 4 grade", "semester average if applicable",
        "grades",
    ),
    "faculty": ("faculty", "fakulte", "fakülte", "faculty/department"),
    "department": ("department", "program", "faculty/department", "dpt code"),
    "entry_year": ("entry year", "entrance year", "giris yili", "giriş yılı"),
    "scholarship": ("scholarship", "scholarship rate", "burs orani", "burs oranı"),
    "kur_code_raw": ("level", "level/section", "module 4 level", "level groups", "els level", "status"),
    "administrative_status": ("recent status", "status", "faculty", "not", "level groups"),
    "student_level": ("student level", "recent status", "status", "faculty", "not", "level groups"),
    "att_booklet": ("r&l absenteeism", "booklet absent", "booklet absenteeism"),
    "att_writing": ("writing absenteeism", "writing absent"),
    "att_speaking": ("speaking absenteeism", "speaking absent"),
    "prep_year_group": ("risk/eligibility", "status", "prep year group"),
}


def aliases(**overrides: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    result = dict(COMMON_ALIASES)
    result.update(overrides)
    return result


SESSIONS: tuple[SessionConfig, ...] = (
    SessionConfig(
        source_session_id="2023-24_EYLUL_01",
        analysis_exam_id="2023-24_EYLUL",
        academic_year="2023-2024",
        slot="EYLUL",
        sitting_order=1,
        file_tokens=("7 8 september epe results final", "september epe results final"),
        sheet_candidates=("TOTAL",),
        header_row=0,
        entry_exam=True,
        expected_id_n=959,
        columns=aliases(
            student_id=("id no",), official_result=("pass/fail",), decision_score=("total",),
            epe_total=("total",), booklet=("rd&ls",), writing=("w",), speaking=("sp",),
            department=("program",), scholarship=("program",), faculty=("fakulte", "fakülte"),
            administrative_status=("not",), student_level=("not",),
        ),
        notes="Ana Eylül oturumu; boş sonuç ve NOT=ABSENT kayıtları devamsız sayılır.",
    ),
    SessionConfig(
        source_session_id="2023-24_EYLUL_02",
        analysis_exam_id="2023-24_EYLUL",
        academic_year="2023-2024",
        slot="EYLUL",
        sitting_order=2,
        file_tokens=("september 21 epe results", "21 eylul", "21 september"),
        sheet_candidates=("Sheet1",),
        header_row=1,
        entry_exam=True,
        expected_id_n=45,
        columns=aliases(
            student_id=("student number",), official_result=("pass/fail",), decision_score=("total",),
            epe_total=("total",), booklet=("rd&ls",), writing=("wr",), speaking=("sp",),
            department=("program",), scholarship=("program",), faculty=("fakulte", "fakülte"),
        ),
        notes="Telafi oturumu; aynı öğrencide son oturum korunur.",
    ),
    SessionConfig(
        source_session_id="2023-24_TEMMUZ_01",
        analysis_exam_id="2023-24_TEMMUZ",
        academic_year="2023-2024",
        slot="HAZIRAN_TEMMUZ",
        sitting_order=1,
        file_tokens=("july 4 5 2024 epe results", "july epe", "4 5 2024 epe"),
        sheet_candidates=("july EPE düzeltilmiş hali", "july epe duzeltilmis hali"),
        header_row=0,
        expected_id_n=406,
        columns=aliases(
            student_id=("student number",), official_result=("pass/fail",),
            decision_score=("total grade",), epe_total=("total",),
            booklet=("rd & ls score",), writing=("wr score",), speaking=("sp score",),
            course_grade=("semester average if applicable",),
            faculty=("faculty/department",), department=("faculty/department",),
            entry_year=("entrance year",), kur_code_raw=("level",),
        ),
    ),
    SessionConfig(
        source_session_id="2024-25_EYLUL_01",
        analysis_exam_id="2024-25_EYLUL",
        academic_year="2024-2025",
        slot="EYLUL",
        sitting_order=1,
        file_tokens=("september epe son gokcen", "september epe_son", "september epe"),
        sheet_candidates=("NİHAİ SONUÇLAR", "NIHAI SONUCLAR"),
        header_row=0,
        entry_exam=True,
        expected_id_n=510,
        columns=aliases(
            student_id=("student no",), official_result=("result",), decision_score=("epe total",),
            epe_total=("epe total",), booklet=("booklet score",), writing=("writing",),
            speaking=("speaking",), faculty=("faculty",), department=("program",),
            scholarship=("program",), entry_year=("entrance year",),
            administrative_status=("faculty",), student_level=("faculty",),
        ),
    ),
    SessionConfig(
        source_session_id="2024-25_OCAK_01",
        analysis_exam_id="2024-25_OCAK",
        academic_year="2024-2025",
        slot="OCAK",
        sitting_order=1,
        file_tokens=("revised after borderline epe grades", "borderline epe grades"),
        sheet_candidates=("revised after borderline (2)",),
        header_row=0,
        expected_id_n=373,
        columns=aliases(
            student_id=("student id",), official_result=("pass/fail",),
            decision_score=("epe passing grade",), epe_total=("epe total",),
            booklet=("epe r&l",), writing=("epe writing",), speaking=("epe speaking",),
            course_grade=("course grade",), faculty=("faculty",), department=("department",),
            entry_year=("entry year",), kur_code_raw=("level/section",),
            att_booklet=("r&l absenteeism",), att_writing=("writing absenteeism",),
            att_speaking=("speaking absenteeism",),
        ),
    ),
    SessionConfig(
        source_session_id="2024-25_HAZIRAN_01",
        analysis_exam_id="2024-25_HAZIRAN",
        academic_year="2024-2025",
        slot="HAZIRAN_TEMMUZ",
        sitting_order=1,
        file_tokens=("student list 16 17 june epe 2025", "june epe 2025 borderline"),
        sheet_candidates=("EPE LIST WITH FORMULA",),
        header_row=0,
        expected_id_n=380,
        columns=aliases(
            student_id=("student id",), official_result=("exit level pass/fail",),
            decision_score=("exit level grade (prep+epe) success only epe",),
            epe_total=("epe total score",), booklet=("epe booklet score",),
            writing=("epe writing score",), speaking=("epe speaking score",),
            course_grade=("module 4 grade",), faculty=("faculty",), department=("department",),
            entry_year=("entry year",), kur_code_raw=("module 4 level",),
            administrative_status=("recent status",), student_level=("recent status",),
        ),
    ),
    SessionConfig(
        source_session_id="2025-26_EYLUL_01",
        analysis_exam_id="2025-26_EYLUL",
        academic_year="2025-2026",
        slot="EYLUL",
        sitting_order=1,
        file_tokens=("september 2025 entry epe", "september_2025_entry_epe"),
        sheet_candidates=("list of sts",),
        header_row=0,
        entry_exam=True,
        expected_id_n=717,
        columns=aliases(
            student_id=("student id",), official_result=("pass/fail",), decision_score=("total score",),
            epe_total=("total score",), booklet=("booklet score",), writing=("writing score",),
            speaking=("speaking score",), faculty=("faculty",), department=("department",),
            scholarship=("scholarship",), entry_year=("entry year",), kur_code_raw=("els level",),
            administrative_status=("status",), student_level=("status",), prep_year_group=("status",),
        ),
    ),
    SessionConfig(
        source_session_id="2025-26_OCAK_01",
        analysis_exam_id="2025-26_OCAK",
        academic_year="2025-2026",
        slot="OCAK",
        sitting_order=1,
        file_tokens=("january epe 2026 all grades after borderline", "january_epe_2026"),
        sheet_candidates=("JAN 2026_epe list",),
        header_row=0,
        expected_id_n=391,
        columns=aliases(
            student_id=("student id",), official_result=("fail/pass",), decision_score=("overall grade",),
            epe_total=("total epe score",), booklet=("epe booklet",), writing=("epe writing",),
            speaking=("epe speaking",), course_grade=("grades",), faculty=("faculty",),
            department=("department",), entry_year=("entry year",), kur_code_raw=("status",),
            administrative_status=("status",), student_level=("status",),
        ),
    ),
    SessionConfig(
        source_session_id="2025-26_HAZIRAN_01",
        analysis_exam_id="2025-26_HAZIRAN",
        academic_year="2025-2026",
        slot="HAZIRAN_TEMMUZ",
        sitting_order=1,
        file_tokens=("june epe 2026 all grades", "june_epe_2026_all_grades"),
        sheet_candidates=("EPE_score_calculation",),
        header_row=0,
        expected_id_n=351,
        columns=aliases(
            student_id=("student id",), official_result=("epe fail/pass",), decision_score=("total score",),
            epe_total=("epe total",), booklet=("epe booklet",), writing=("epe writing",),
            speaking=("epe speaking",), course_grade=("course grades",), department=("department",),
            entry_year=("entry year",), kur_code_raw=("level groups",),
            administrative_status=("level groups",), student_level=("level groups",),
            att_booklet=("booklet absent",), att_writing=("writing absent",),
            att_speaking=("speaking absent",), faculty=("dpt code",),
        ),
    ),
)


REGISTRY_SHEETS: dict[str, tuple[str, ...]] = {
    "2023-2024": ("2023-2024",),
    "2024-2025": ("2024-2025 ÖGR YILI MAIN DATA", "2024-2025 OGR YILI MAIN DATA"),
    "2025-2026": ("ALL SS_MODÜL 4 SONU", "ALL SS_MODUL 4 SONU"),
}

OTHER_UG_THRESHOLD = 64.50
ELL_ELT_THRESHOLD = 74.50
ROUNDING_TOLERANCE = 0.05

ELL_ELT_KEYWORDS = (
    "english language teaching", "english language and literature", "english language literature",
    "ingiliz dili ve edebiyati", "ingiliz dili ve edebiyatı", "ingilizce ogretmenligi",
    "ingilizce öğretmenliği", "elt", "ell",
)

FINAL_RESULT_VALUES = {"PASS", "FAIL"}
