# EPE Raporlama Aracı

Bu klasör, dashboard kullanmadan EPE sonuç dosyaları ve öğrenci kütüklerinden Word raporu, PowerPoint sunumu ve Excel veri kalite özeti üretmek için oluşturulmuştur.

## Kurulum

Windows Anaconda Prompt içinde:

```bat
cd /d "PROJE_KLASORU\epe-report-tool"
conda create -n epe-reporting python=3.11 -y
conda activate epe-reporting
pip install -r requirements.txt
```

Güvenli öğrenci hash'i için aynı gizli anahtarı her çalıştırmada kullanın:

```bat
set EPE_HMAC_KEY=UZUN_RASTGELE_GIZLI_ANAHTAR
```

## Çalıştırma

```bat
python run_report.py
```

Araç sırayla:

1. EPE sonuç Excel dosyalarını seçtirir.
2. Öğrenci kütüklerini seçtirir.
3. Çıktı klasörünü seçtirir.
4. Word, PowerPoint ve Excel çıktılarını aynı çalışma hattından üretir.

## İlk sürümün mevcut kapsamı

Bu ilk commit çalışan dosya seçim ve çıktı üretim omurgasıdır. Seçilen Excel dosyalarının sayfalarını okuyarak kaynak envanteri ve veri kalite özeti üretir. Sonraki commitlerde aşağıdaki analiz katmanları aynı giriş noktasına eklenir:

- oturum tanıma ve eşleme tablosu uygulaması,
- 2023–2024 Ocak EPE'nin kütükten kısmi analizi,
- PASS/FAIL ve Wilson güven aralıkları,
- karar eşiğine göre bant ve near-miss,
- ELL–ELT / diğer lisans ayrımı,
- fakülte ve burs tabloları,
- beceri profilleri,
- 12 temel soruya göre Word ve PowerPoint bölümleri.

## Ocak 2024

Orijinal sınav dosyası olmadan kütükten genel sonuç, karar puanı, bant, near-miss, fakülte ve burs üretilecektir. Booklet, Writing ve Speaking bulunmadığından beceri analizi atlanacaktır. Orijinal dosya sonradan eklendiğinde aynı `2023-24_OCAK` oturumu beceri alanlarıyla genişletilecektir.
