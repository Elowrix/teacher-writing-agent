from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from epe_report_tool.runner import ReportRunner


def choose_files(title: str, *, allow_zip: bool = False) -> list[Path]:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filetypes = [("Excel files", "*.xlsx *.xlsm")]
    if allow_zip:
        filetypes.insert(0, ("EPE archive or Excel files", "*.zip *.xlsx *.xlsm"))
    filetypes.append(("All files", "*.*"))
    paths = filedialog.askopenfilenames(title=title, filetypes=filetypes)
    root.destroy()
    return [Path(p) for p in paths]


def choose_directory(title: str) -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return Path(path) if path else None


def expand_epe_sources(selected_paths: list[Path], temp_root: Path) -> list[Path]:
    """Return Excel sources, extracting ZIP archives into a temporary folder.

    Unsafe archive paths are rejected. Only .xlsx and .xlsm files are passed to
    the analysis engine; unrelated files inside the archive are ignored.
    """
    excel_files: list[Path] = []
    for selected in selected_paths:
        if selected.suffix.lower() != ".zip":
            excel_files.append(selected)
            continue

        archive_dir = temp_root / selected.stem
        archive_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(selected) as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member.is_dir() or member_path.suffix.lower() not in {".xlsx", ".xlsm"}:
                    continue
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError(f"ZIP içinde güvenli olmayan yol bulundu: {member.filename}")
                target = archive_dir / member_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as destination:
                    destination.write(source.read())
                excel_files.append(target)

    if not excel_files:
        raise ValueError("Seçilen EPE kaynağında analiz edilebilir Excel dosyası bulunamadı.")
    return excel_files


def main() -> int:
    print("EPE Raporlama Aracı")
    print("1/3: EPE ZIP arşivini veya EPE sonuç Excel dosyalarını seçin.")
    selected_epe_sources = choose_files(
        "EPE ZIP arşivini veya EPE sonuç Excel dosyalarını seçin",
        allow_zip=True,
    )
    if not selected_epe_sources:
        print("EPE kaynağı seçilmedi; işlem iptal edildi.")
        return 1

    print("2/3: Öğrenci kütüklerini seçin.")
    registry_files = choose_files("Öğrenci kütüklerini seçin")
    if not registry_files:
        print("Öğrenci kütüğü seçilmedi; işlem iptal edildi.")
        return 1

    print("3/3: Çıktı klasörünü seçin.")
    output_dir = choose_directory("Word, PowerPoint ve Excel çıktı klasörünü seçin")
    if output_dir is None:
        print("Çıktı klasörü seçilmedi; işlem iptal edildi.")
        return 1

    secret = os.environ.get("EPE_HMAC_KEY")
    if not secret:
        print("UYARI: EPE_HMAC_KEY tanımlı değil. Yerel önizleme anahtarı kullanılacak.")
        secret = "LOCAL_PREVIEW_ONLY_CHANGE_ME"

    runner = ReportRunner(project_root=Path(__file__).resolve().parent, hmac_secret=secret)
    try:
        with tempfile.TemporaryDirectory(prefix="epe_report_") as temp_dir:
            epe_files = expand_epe_sources(selected_epe_sources, Path(temp_dir))
            print(f"{len(epe_files)} EPE Excel dosyası analize hazırlandı.")
            outputs = runner.run(
                epe_files=epe_files,
                registry_files=registry_files,
                output_dir=output_dir,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"HATA: {exc}")
        return 2

    print("\nRapor üretimi tamamlandı:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")

    root = Tk()
    root.withdraw()
    messagebox.showinfo(
        "EPE Raporlama Aracı",
        "Rapor üretimi tamamlandı.\n\n" + "\n".join(str(p) for p in outputs.values()),
    )
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
