import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
from yt_dlp import YoutubeDL


ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "kaynaklar.txt"
POSTED_FILE = ROOT / "paylasilanlar.json"
DOWNLOAD_DIR = ROOT / "downloads"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN", "").strip()
MAX_SCAN_PER_SOURCE = int(os.getenv("MAX_SCAN_PER_SOURCE", "8"))
MAX_POSTS_PER_RUN = int(os.getenv("MAX_POSTS_PER_RUN", "20"))
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "45"))


def log(message: str) -> None:
    print(message, flush=True)


def load_sources() -> List[str]:
    if not SOURCES_FILE.exists():
        raise FileNotFoundError("kaynaklar.txt bulunamadı.")
    sources = []
    for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            sources.append(line)
    return sources


def load_posted() -> Dict[str, Any]:
    if not POSTED_FILE.exists():
        return {"posted": []}
    try:
        return json.loads(POSTED_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"posted": []}


def save_posted(data: Dict[str, Any]) -> None:
    POSTED_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def normalize_candidate(entry: Dict[str, Any], source: str) -> Optional[Dict[str, str]]:
    video_id = entry.get("id") or entry.get("url") or entry.get("webpage_url")
    url = entry.get("webpage_url") or entry.get("url")

    if url and not str(url).startswith("http"):
        extractor_key = (entry.get("ie_key") or "").lower()
        if "youtube" in extractor_key or "youtube" in source:
            url = f"https://www.youtube.com/watch?v={url}"

    if not video_id or not url:
        return None

    title = entry.get("title") or "Video"
    return {
        "id": str(video_id),
        "url": str(url),
        "title": str(title),
        "source": source,
    }


def collect_candidates(source: str) -> List[Dict[str, str]]:
    opts = {
        "quiet": True,
        "extract_flat": True,
        "playlistend": MAX_SCAN_PER_SOURCE,
        "ignoreerrors": True,
        "skip_download": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source, download=False)

    candidates = []

    if not info:
        return candidates

    if "entries" in info and info["entries"]:
        for entry in info["entries"]:
            if not entry:
                continue
            candidate = normalize_candidate(entry, source)
            if candidate:
                candidates.append(candidate)
    else:
        candidate = normalize_candidate(info, source)
        if candidate:
            candidates.append(candidate)

    return candidates


def download_video(candidate: Dict[str, str]) -> Optional[Path]:
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    output_tpl = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")
    opts = {
        "quiet": False,
        "outtmpl": output_tpl,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": MAX_VIDEO_MB * 1024 * 1024,
        "ignoreerrors": True,
        "retries": 3,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(candidate["url"], download=True)

    if not info:
        return None

    vid = str(info.get("id") or candidate["id"])
    matches = list(DOWNLOAD_DIR.glob(f"{vid}.*"))

    if not matches:
        return None

    matches.sort(key=lambda p: p.stat().st_size, reverse=True)
    path = matches[0]

    if path.stat().st_size > MAX_VIDEO_MB * 1024 * 1024:
        log(f"Atlandı, dosya çok büyük: {path.name}")
        return None

    return path


def send_to_telegram(video_path: Path, candidate: Dict[str, str]) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID secret olarak eklenmeli.")

    caption = candidate["title"][:900]
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    with video_path.open("rb") as f:
        response = requests.post(
            api_url,
            data={
                "chat_id": CHAT_ID,
                "caption": caption,
                "supports_streaming": "true",
            },
            files={"video": f},
            timeout=120,
        )

    if response.ok:
        return True

    log(f"Telegram sendVideo hatası: {response.status_code} {response.text[:500]}")
    return False
def send_to_facebook(video_path: Path, candidate: Dict[str, str]) -> bool:
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_TOKEN:
        raise RuntimeError(
            "FACEBOOK_PAGE_ID ve FACEBOOK_PAGE_TOKEN secret olarak eklenmeli."
        )

    url = f"https://graph-video.facebook.com/{FACEBOOK_PAGE_ID}/videos"

    with video_path.open("rb") as f:
        response = requests.post(
            url,
            data={
                "access_token": FACEBOOK_PAGE_TOKEN,
                "description": candidate["title"],
            },
            files={"source": f},
            timeout=600,
        )

    if response.ok:
        log("Facebook'a gönderildi.")
        return True

    log(
        f"Facebook video yükleme hatası: "
        f"{response.status_code} {response.text[:500]}"
    )
    return False

def main() -> int:
    posted_data = load_posted()
    posted = set(posted_data.get("posted", []))

    sources = load_sources()
    if not sources:
        log("Kaynak yok. kaynaklar.txt içine kanal/playlist/video linki ekle.")
        return 0

    posted_this_run = 0

    for source in sources:
        log(f"Kaynak taranıyor: {source}")
        try:
            candidates = collect_candidates(source)
        except Exception as exc:
            log(f"Kaynak okunamadı: {source} | {exc}")
            continue

        for candidate in candidates:
            unique_key = candidate["id"]

            if unique_key in posted:
                log(f"Zaten paylaşılmış: {candidate['title']}")
                continue

            if posted_this_run >= MAX_POSTS_PER_RUN:
                save_posted(posted_data)
                log("Bu çalıştırma için paylaşım limiti doldu.")
                return 0

            log(f"İndiriliyor: {candidate['title']}")

            try:
                video_path = download_video(candidate)
            except Exception as exc:
                log(f"İndirme hatası: {candidate['url']} | {exc}")
                continue

            if not video_path:
                log(f"Video indirilemedi veya uygun değil: {candidate['url']}")
                continue

            log(f"Telegram'a gönderiliyor: {video_path.name}")

            try:
                sent = send_to_facebook(video_path, candidate)
            except Exception as exc:
                log(f"Telegram gönderim hatası: {exc}")
                sent = False

            if sent:
                posted.add(unique_key)
                posted_data["posted"] = sorted(posted)
                save_posted(posted_data)
                posted_this_run += 1
                log(f"Paylaşıldı: {candidate['title']}")
            else:
                log(f"Paylaşılamadı: {candidate['title']}")

            try:
                video_path.unlink(missing_ok=True)
            except Exception:
                pass

    save_posted(posted_data)
    log(f"Tamamlandı. Bu çalıştırmada paylaşılan: {posted_this_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
