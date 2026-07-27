from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt


QUESTIONS = (
    ("Q1", "PASS/FAIL oranları yıllar içinde nasıl değişti?"),
    ("Q2", "Kalanların ne kadarı eşiğin ilk 5 puanı içinde?"),
    ("Q3", "Geçenlerin ne kadarı sınırda geçti?"),
    ("Q4", "ELL–ELT ile diğer lisans programlarının sonuçları nasıl farklılaşıyor?"),
    ("Q5", "Near-miss hangi fakültelerde yoğunlaşıyor?"),
    ("Q6–Q7", "Burs gruplarının sonuçları fakültelere göre nasıl değişiyor?"),
    ("Q8–Q10", "Eşik çevresindeki öğrencilerin beceri profilleri nasıl farklılaşıyor?"),
    ("Q11", "Giriş ve dönem içi EPE’lerde toplam puan ve beceri profilleri nasıl farklılaşıyor?"),
    ("Q12", "Öğrenciler eşik çevresinde mi yoğunlaşıyor?"),
)


def pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"%{float(value) * 100:.1f}"


def number(value: object, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}"


def _add_docx_table(document: Document, frame: pd.DataFrame, columns: list[tuple[str, str]], max_rows: int = 50) -> None:
    if frame.empty:
        document.add_paragraph("Bu bölüm için kullanılabilir veri bulunmamaktadır.")
        return
    shown = frame.head(max_rows)
    table = document.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    for idx, (_, label) in enumerate(columns):
        table.rows[0].cells[idx].text = label
    for _, row in shown.iterrows():
        cells = table.add_row().cells
        for idx, (field, _) in enumerate(columns):
            value = row.get(field)
            if field.lower().endswith("rate") or field.startswith("Wilson"):
                cells[idx].text = pct(value)
            else:
                cells[idx].text = "—" if value is None or pd.isna(value) else str(value)
    if len(frame) > max_rows:
        document.add_paragraph(f"Tablonun ilk {max_rows} satırı gösterilmiştir. Tam tablo Excel ekindedir.")


def write_excel(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in tables.items():
            safe_name = name[:31]
            frame.to_excel(writer, sheet_name=safe_name, index=False)
            sheet = writer.book[safe_name]
            sheet.freeze_panes = "A2"
            for column_cells in sheet.columns:
                width = min(max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells) + 2, 45)
                sheet.column_dimensions[column_cells[0].column_letter].width = width


def _create_pass_chart(result_table: pd.DataFrame, path: Path) -> None:
    chart = result_table.copy()
    chart["label"] = chart["analysis_exam_id"].astype(str)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(chart["label"], chart["PASS_rate"] * 100)
    ax.set_ylabel("PASS (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Oturum Bazında PASS Oranı")
    ax.tick_params(axis="x", rotation=45)
    for index, value in enumerate(chart["PASS_rate"] * 100):
        ax.text(index, value + 1.2, f"%{value:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _create_near_chart(near_table: pd.DataFrame, path: Path) -> None:
    chart = near_table.copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(chart["analysis_exam_id"].astype(str), chart["near_miss_rate_among_FAIL"].fillna(0) * 100)
    ax.set_ylabel("FAIL içinde near-miss (%)")
    ax.set_ylim(0, max(20, float((chart["near_miss_rate_among_FAIL"].fillna(0) * 100).max()) + 8))
    ax.set_title("FAIL Grubu İçinde Eşiğin İlk 5 Puanında Kalanlar")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_word(path: Path, tables: dict[str, pd.DataFrame], coverage_note: str) -> None:
    result_table = tables.get("Genel Sonuclar", pd.DataFrame())
    near_table = tables.get("Near Miss", pd.DataFrame())
    threshold_table = tables.get("Esik Gruplari", pd.DataFrame())
    faculty_table = tables.get("Fakulte Burs", pd.DataFrame())
    skill_table = tables.get("Beceri Profili", pd.DataFrame())
    validation_table = tables.get("Dogrulama", pd.DataFrame())
    quality_table = tables.get("Kaynak Kalitesi", pd.DataFrame())

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    styles = document.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)
    title = document.add_heading("EPE Yıllar Arası Analiz Raporu", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph("Eylül, Ocak ve Haziran/Temmuz EPE Oturumları")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    document.add_heading("Yönetici Özeti", level=1)
    document.add_paragraph(
        "Bu rapor, aynı EPE yuvasındaki oturumları yıllar arasında karşılaştırır. Resmî PASS/FAIL sonucu "
        "esas alınmış; karar puanı öğrencinin kendi program eşiğine uzaklığı, bant ve near-miss analizi için kullanılmıştır."
    )
    document.add_paragraph(coverage_note)

    document.add_heading("Kapsam ve Yöntem", level=1)
    for text in (
        "Diğer lisans programları için karar eşiği 64,50; ELL–ELT grubu için 74,50'dir.",
        "Near-miss: resmî sonucu FAIL olan ve karar puanı kendi eşiğinin 0–5 puan altında bulunan öğrenci.",
        "Sınırda geçen: resmî sonucu PASS olan ve karar puanı kendi eşiğinin 0–5 puan üstünde bulunan öğrenci.",
        "Aynı öğrencinin aynı analiz oturumunda birden fazla kaydı varsa son sitting korunur.",
        "Beceri analizleri yalnız Booklet, Writing ve Speaking puanlarının üçü de bulunan kayıtlarda yapılır.",
        "N<5 hücreler yorumlanmamalı; N=5–9 dikkatli, N≥10 karşılaştırılabilir kabul edilmelidir.",
    ):
        document.add_paragraph(text, style="List Bullet")

    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        if not result_table.empty:
            chart_path = temp / "pass.png"
            _create_pass_chart(result_table, chart_path)
            document.add_heading("Q1. PASS/FAIL Oranlarının Yıllar İçindeki Değişimi", level=1)
            document.add_picture(str(chart_path), width=Inches(7.0))
            _add_docx_table(document, result_table, [
                ("analysis_exam_id", "Oturum"), ("N", "N"), ("PASS", "PASS"),
                ("FAIL", "FAIL"), ("PASS_rate", "PASS oranı"),
                ("Wilson_lower", "%95 GA alt"), ("Wilson_upper", "%95 GA üst"),
            ])

        document.add_heading("Q2–Q3. Near-miss ve Sınırda Geçenler", level=1)
        if not near_table.empty:
            chart_path = temp / "near.png"
            _create_near_chart(near_table, chart_path)
            document.add_picture(str(chart_path), width=Inches(7.0))
        _add_docx_table(document, near_table, [
            ("analysis_exam_id", "Oturum"), ("FAIL_N", "FAIL N"),
            ("near_miss_N", "Near-miss N"), ("near_miss_rate_among_FAIL", "FAIL içinde oran"),
            ("PASS_N", "PASS N"), ("borderline_pass_N", "Sınırda geçen N"),
            ("borderline_rate_among_PASS", "PASS içinde oran"),
        ])

    document.add_heading("Q4. ELL–ELT ve Diğer Lisans Programları", level=1)
    _add_docx_table(document, threshold_table, [
        ("analysis_exam_id", "Oturum"), ("threshold_group", "Eşik grubu"),
        ("N", "N"), ("PASS", "PASS"), ("FAIL", "FAIL"), ("PASS_rate", "PASS oranı"),
    ])

    document.add_heading("Q5–Q7. Fakülte ve Burs Görünümü", level=1)
    document.add_paragraph(
        "Aşağıdaki sonuçlar betimseldir. Küçük hücrelerde yüzdeler kurumsal kararın tek dayanağı olarak kullanılmamalıdır."
    )
    _add_docx_table(document, faculty_table, [
        ("analysis_exam_id", "Oturum"), ("faculty", "Fakülte"),
        ("scholarship", "Burs"), ("N", "N"), ("PASS_rate", "PASS oranı"),
        ("near_miss_N", "Near-miss N"), ("near_miss_rate_among_FAIL", "FAIL içinde near-miss"),
    ], max_rows=80)

    document.add_heading("Q8–Q10. Eşik Çevresinde Beceri Profilleri", level=1)
    document.add_paragraph(
        "Productive puan Writing+Speaking; Receptive puan Booklet üzerinden yüzdeye dönüştürülmüştür. "
        "Ocak 2024 orijinal EPE dosyası bulunmadığı sürece bu oturum beceri analizinde gösterilmez."
    )
    _add_docx_table(document, skill_table, [
        ("analysis_exam_id", "Oturum"), ("threshold_side", "Eşik tarafı"), ("N", "N"),
        ("receptive_pct", "Receptive %"), ("productive_pct", "Productive %"),
        ("writing_pct", "Writing %"), ("speaking_pct", "Speaking %"),
        ("productive_minus_receptive", "Prod.–Rec."),
        ("writing_minus_speaking", "Writing–Speaking"),
    ])

    document.add_heading("Q11–Q12. Giriş/Dönem İçi Görünüm ve Eşik Çevresi", level=1)
    document.add_paragraph(
        "Giriş sınavları ile dönem içi sınavlar farklı öğrenci popülasyonlarını temsil eder. Bu nedenle ana yorumlar aynı yuva içinde "
        "yıllar arasında yapılmalı; giriş ve dönem içi sınavlar doğrudan başarı sıralaması olarak okunmamalıdır."
    )
    _add_docx_table(document, tables.get("Bantlar", pd.DataFrame()), [
        ("analysis_exam_id", "Oturum"), ("band", "Eşik bandı"), ("N", "N"),
    ])

    document.add_heading("Veri Kalitesi ve Doğrulama", level=1)
    _add_docx_table(document, quality_table, [
        ("file", "Dosya"), ("analysis_exam_id", "Oturum"), ("id_n", "ID dolu N"),
        ("expected_id_n", "Beklenen N"), ("id_n_match", "N uyumu"),
        ("result_n", "PASS/FAIL N"), ("decision_score_n", "Karar puanı N"),
        ("skill_complete_n", "Tam beceri N"), ("status", "Durum"),
    ])
    _add_docx_table(document, validation_table, [
        ("analysis_exam_id", "Oturum"), ("result_threshold_validation", "Kontrol"), ("N", "N"),
    ])

    document.add_heading("Kurumsal Değerlendirme Alanı", level=1)
    document.add_paragraph(
        "Bu bölüm, sonuçların program hedefleri, sınav uygulamaları ve öğrenci destek kararları açısından kurum tarafından yorumlanması için ayrılmıştır."
    )
    document.add_paragraph("\n" * 5)
    document.save(path)


def _add_ppt_table(slide, frame: pd.DataFrame, columns: list[tuple[str, str]], max_rows: int = 8) -> None:
    if frame.empty:
        textbox = slide.shapes.add_textbox(PptInches(0.8), PptInches(1.8), PptInches(8.5), PptInches(3.5))
        textbox.text_frame.text = "Bu bölüm için kullanılabilir veri bulunmamaktadır."
        return
    shown = frame.head(max_rows)
    shape = slide.shapes.add_table(len(shown) + 1, len(columns), PptInches(0.4), PptInches(1.35), PptInches(9.2), PptInches(5.5))
    table = shape.table
    for idx, (_, label) in enumerate(columns):
        table.cell(0, idx).text = label
    for row_idx, (_, row) in enumerate(shown.iterrows(), start=1):
        for col_idx, (field, _) in enumerate(columns):
            value = row.get(field)
            if field.lower().endswith("rate"):
                text = pct(value)
            elif field.endswith("_pct") or "minus" in field:
                text = number(value)
            else:
                text = "—" if value is None or pd.isna(value) else str(value)
            table.cell(row_idx, col_idx).text = text
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = PptPt(11)


def _new_title_slide(prs: Presentation, title: str, subtitle: str = ""):
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = subtitle
    return slide


def _new_content_slide(prs: Presentation, title: str):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    return slide


def write_powerpoint(path: Path, tables: dict[str, pd.DataFrame], coverage_note: str) -> None:
    result_table = tables.get("Genel Sonuclar", pd.DataFrame())
    near_table = tables.get("Near Miss", pd.DataFrame())
    threshold_table = tables.get("Esik Gruplari", pd.DataFrame())
    skill_table = tables.get("Beceri Profili", pd.DataFrame())
    quality_table = tables.get("Kaynak Kalitesi", pd.DataFrame())

    prs = Presentation()
    prs.slide_width = PptInches(13.333)
    prs.slide_height = PptInches(7.5)
    _new_title_slide(prs, "EPE Yıllar Arası Analiz", "Yönetim için karar odaklı sonuç sunumu")

    slide = _new_content_slide(prs, "Kapsam ve Okuma İlkeleri")
    textbox = slide.shapes.add_textbox(PptInches(0.8), PptInches(1.5), PptInches(11.8), PptInches(4.9))
    tf = textbox.text_frame
    principles = [
        coverage_note,
        "Karşılaştırmalar aynı EPE yuvası içinde yıllar arasında yapılır.",
        "Near-miss resmî FAIL grubunda, öğrencinin kendi eşiğinin 0–5 puan altıdır.",
        "Resmî PASS/FAIL sonucu değiştirilmez.",
        "N<5 yorumlanmaz; N=5–9 dikkatli okunur.",
    ]
    for idx, item in enumerate(principles):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = PptPt(22)
        p.space_after = PptPt(12)

    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        if not result_table.empty:
            chart = temp / "pass.png"
            _create_pass_chart(result_table, chart)
            slide = _new_content_slide(prs, "PASS Oranları: Oturum Bazında Görünüm")
            slide.shapes.add_picture(str(chart), PptInches(1.0), PptInches(1.35), width=PptInches(11.2))

        slide = _new_content_slide(prs, "PASS/FAIL Sonuç Tablosu")
        _add_ppt_table(slide, result_table, [
            ("analysis_exam_id", "Oturum"), ("N", "N"), ("PASS", "PASS"),
            ("FAIL", "FAIL"), ("PASS_rate", "PASS %"),
        ], max_rows=10)

        if not near_table.empty:
            chart = temp / "near.png"
            _create_near_chart(near_table, chart)
            slide = _new_content_slide(prs, "Eşiğin İlk 5 Puanında Kalanlar")
            slide.shapes.add_picture(str(chart), PptInches(1.0), PptInches(1.35), width=PptInches(11.2))

    slide = _new_content_slide(prs, "Near-miss ve Sınırda Geçenler")
    _add_ppt_table(slide, near_table, [
        ("analysis_exam_id", "Oturum"), ("FAIL_N", "FAIL N"),
        ("near_miss_N", "Near-miss"), ("near_miss_rate_among_FAIL", "FAIL içi %"),
        ("borderline_pass_N", "Sınırda PASS"),
    ], max_rows=10)

    slide = _new_content_slide(prs, "ELL–ELT ve Diğer Lisans Programları")
    _add_ppt_table(slide, threshold_table, [
        ("analysis_exam_id", "Oturum"), ("threshold_group", "Grup"),
        ("N", "N"), ("PASS", "PASS"), ("PASS_rate", "PASS %"),
    ], max_rows=10)

    slide = _new_content_slide(prs, "Beceri Profili: Eşiğin Altı ve Üstü")
    _add_ppt_table(slide, skill_table, [
        ("analysis_exam_id", "Oturum"), ("threshold_side", "Konum"), ("N", "N"),
        ("receptive_pct", "Rec. %"), ("productive_pct", "Prod. %"),
        ("writing_pct", "Wr. %"), ("speaking_pct", "Sp. %"),
    ], max_rows=10)

    slide = _new_content_slide(prs, "Veri Kalitesi")
    _add_ppt_table(slide, quality_table, [
        ("analysis_exam_id", "Oturum"), ("id_n", "ID N"), ("expected_id_n", "Beklenen"),
        ("id_n_match", "Uyum"), ("result_n", "Sonuç N"), ("skill_complete_n", "Beceri N"),
    ], max_rows=10)

    slide = _new_content_slide(prs, "Karar İçin Öne Çıkan Sorular")
    textbox = slide.shapes.add_textbox(PptInches(0.9), PptInches(1.4), PptInches(11.6), PptInches(5.2))
    tf = textbox.text_frame
    prompts = [
        "Eşik çevresindeki yoğunluk öğrenci desteği veya sınav hazırlığı açısından ne söylüyor?",
        "Aynı yuvada yıllar arası değişimin ne kadarı öğrenci bileşimiyle açıklanabilir?",
        "Fakülte ve burs kırılımlarında kalıcı görünen örüntüler var mı?",
        "Productive–Receptive ve Writing–Speaking profilleri hangi destek alanlarına işaret ediyor?",
        "Hangi bulgular ek veri veya kurumsal bağlam olmadan yorumlanmamalı?",
    ]
    for idx, item in enumerate(prompts):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = PptPt(23)
        p.space_after = PptPt(14)

    prs.save(path)
