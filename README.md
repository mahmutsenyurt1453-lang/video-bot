# Telegram Video Otomasyonu

Bu sistem videoları kaynaklardan otomatik bulur, indirir ve Telegram kanalına gönderir.

## Mantık

```text
kaynaklar.txt
  ↓
GitHub Actions otomatik çalışır
  ↓
yt-dlp ile yeni video aranır
  ↓
video indirilir
  ↓
Telegram kanalına gönderilir
  ↓
paylasilanlar.json güncellenir
```

## Kurulum

### 1. Telegram bot oluştur

Telegram'da `@BotFather` hesabına gir.

Şu komutu gönder:

```text
/newbot
```

Bot adını oluştur. BotFather sana bir token verecek.

Bu token şu formatta olur:

```text
123456789:ABCDEF...
```

### 2. Telegram kanalı oluştur

Telegram'da bir kanal oluştur.

Botu kanala admin olarak ekle.

### 3. Kanal ID bilgisini al

Kolay yöntem:

Kanal herkese açıksa `TELEGRAM_CHAT_ID` olarak şunu kullanabilirsin:

```text
@kanal_kullanici_adi
```

Örnek:

```text
@benimvideokanalim
```

Kanal gizliyse kanal ID gerekir. İlk kurulumda herkese açık kanal kullanmak daha kolaydır.

### 4. GitHub repo oluştur

GitHub'da yeni bir repository oluştur.

Bu klasördeki dosyaları repo içine yükle.

Dosya yapısı şöyle olmalı:

```text
main.py
requirements.txt
kaynaklar.txt
paylasilanlar.json
.github/workflows/video-bot.yml
```

### 5. GitHub Secrets ekle

GitHub reposunda:

```text
Settings → Secrets and variables → Actions → New repository secret
```

Şu iki secret eklenecek:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

### 6. Kaynakları ekle

`kaynaklar.txt` içine her satıra bir kaynak yaz.

Örnek:

```text
https://www.youtube.com/@KANAL_ADI/shorts
https://www.youtube.com/playlist?list=PLAYLIST_ID
```

### 7. İlk test

GitHub reposunda:

```text
Actions → Telegram Video Bot → Run workflow
```

Çalışırsa Telegram kanalına video gönderir.

## Ayarlar

`.github/workflows/video-bot.yml` içinde şu değerler değiştirilebilir:

```text
MAX_SCAN_PER_SOURCE: Her kaynakta kaç video taransın
MAX_POSTS_PER_RUN: Her çalışmada kaç video paylaşılsın
MAX_VIDEO_MB: En fazla kaç MB video gönderilsin
```

Varsayılan:

```text
MAX_SCAN_PER_SOURCE = 8
MAX_POSTS_PER_RUN = 2
MAX_VIDEO_MB = 45
```

## Çalışma saatleri

Varsayılan sistem Türkiye saatiyle günde 3 kez çalışır:

```text
09:00
15:00
21:00
```

GitHub cron UTC çalışır. Türkiye saati UTC+3 olduğu için workflow içinde 06,12,18 UTC yazılmıştır.

## Önemli not

Bu sistem teknik otomasyon sağlar. Paylaşılan videolar için telif hakkı, platform kuralları ve içerik izinleri sana aittir.
Yalnızca paylaşma hakkın olan içerikleri kullanman önerilir.
