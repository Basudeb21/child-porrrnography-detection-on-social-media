import os
import time
import sys
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import NSFW detector
from db.nsfw_detector import NSFWDetector  # adjust if needed

BASE_URL = "http://localhost:8000/images"  # Publicly served URL for images
IMAGES_DIR = str(Path(__file__).parent.parent / "storage" / "filter" / "minor" / "nonfilter")
MODEL_PATH = str(Path(__file__).parent.parent / "mobilenet_v2_140_224")
THRESHOLD = 0.8

MODERATION_API_BASE = "http://127.0.0.1:8000"
MODERATION_ENDPOINT = f"{MODERATION_API_BASE}/moderation/"

# Defaults
DEFAULT_TABLE_NAME = "posts"
DEFAULT_POST_TYPE = "img"
DEFAULT_STATUS = "reported"
DEFAULT_USER_ID = 0

# Report rule
REPORT_PERCENT = 30.0


def send_to_moderation_api(file_url: str,
                           post_type: str = DEFAULT_POST_TYPE,
                           table_name: str = DEFAULT_TABLE_NAME,
                           reason: str = "",
                           user_id: int = DEFAULT_USER_ID,
                           status: str = DEFAULT_STATUS,
                           retries: int = 3,
                           timeout: int = 6):
    payload = {
        "url": file_url,
        "post_type": post_type,
        "table_name": table_name,
        "reason": reason,
        "user_id": user_id,
        "status": status
    }

    last_err = None
    for _ in range(retries):
        try:
            r = requests.post(MODERATION_ENDPOINT, json=payload, timeout=timeout)
            if r.status_code in (200, 201):
                print(f"[API] Moderation recorded: {r.json()}")
                return True
            else:
                print(f"[API] Failed ({r.status_code}): {r.text}")
                last_err = r.text
        except Exception as e:
            print(f"[API] Error: {e}")
            last_err = str(e)
        time.sleep(0.8)

    print(f"[API] Giving up after retries. Last error: {last_err}")
    return False


class ImageHandler(FileSystemEventHandler):
    def __init__(self):
        self.detector = NSFWDetector(MODEL_PATH)

    def on_created(self, event):
        if event.is_directory:
            return
        low = event.src_path.lower()
        if not (low.endswith(".png") or low.endswith(".jpg") or low.endswith(".jpeg")):
            return

        print(f"\nFile Detected: {event.src_path}")
        self.process_image(event.src_path)

    def process_image(self, image_path: str):
        print(f"Processing new image: {os.path.basename(image_path)}")

        try:
            # Run NSFW detector
            result = self.detector.predict(image_path, THRESHOLD)

            if result.get('error'):
                print(f"Detection error: {result['error']}")
                return

            scores = result.get("scores", {})
            sexy_pct = float(scores.get("sexy", 0.0))
            porn_pct = float(scores.get("porn", 0.0))
            hentai_pct = float(scores.get("hentai", 0.0))
            is_nsfw = bool(result.get("is_nsfw", False))

            print("\nDetection Results:")
            for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                print(f"{label.upper()+':':<10} {score:.2f}%")
            print(f"NSFW: {'YES' if is_nsfw else 'NO'}")

            should_report = (porn_pct >= REPORT_PERCENT) or (sexy_pct >= REPORT_PERCENT)

            file_url = f"{BASE_URL}/{os.path.basename(image_path)}"

            if should_report:
                if sexy_pct > porn_pct:
                    extra_reason = "Post contains nude image of kids."
                elif porn_pct > sexy_pct:
                    extra_reason = "Post contains pornographic contents of kids."
                else:
                    extra_reason = "Post flagged for unsafe minor content."

                reason = (
                    f"Minor detected with NSFW indicators. "
                    f"{extra_reason}"
                )

                ok = send_to_moderation_api(
                    file_url=file_url,
                    post_type="img",
                    table_name=DEFAULT_TABLE_NAME,
                    reason=reason,
                    user_id=DEFAULT_USER_ID,
                    status="reported"
                )
                if ok:
                    print("Report created in moderation service")
                else:
                    print("Failed to create moderation report")

        except Exception as e:
            print(f"Processing failed: {str(e)}")

        finally:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Deleted image: {image_path}")
            except Exception as e:
                print(f"Failed to delete image {image_path}: {e}")


if __name__ == "__main__":
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        print(f"Created images directory at {IMAGES_DIR}")

    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        sys.exit(1)

    # Start watcher
    print(f"\nStarting image watcher on: {IMAGES_DIR}")
    print(f"Using model: {MODEL_PATH}")
    print(f"NSFW Threshold: {THRESHOLD*100}%")
    print(f"Report Rule: age<18 AND (porn≥{REPORT_PERCENT}% OR sexy≥{REPORT_PERCENT}%)")
    print("Press Ctrl+C to stop\n")

    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, IMAGES_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
