from __future__ import annotations

import os
import sys
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from epe_report_tool.runner import ReportRunner


def choose_files(title: str) -> list[Path]:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    paths = filedialog.askopenfilenames(
        title=title,
        filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
    )
    root.destroy()
    return [Path(p) for p in paths]


def choose_directory(title: str) -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return Path(path) if path else None


def main() -> int:
    print("EPE Raporlama Aracı")
    print("1/3: EPE sonuç dosyalarını seçin.")
    epe_files = choose_files("EPE sonuç dosyalarını seçin")
    if not epe_files:
        print("EPE dosyası seçilmedi; işlem iptal edildi.")
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
