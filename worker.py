import os
import cv2
import redis
import time
import json
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
import requests

# ────────── Import your modules ──────────
from nsfw.nsfw_detector import NSFWDetector
from animal_detect.animal_porn_detect import has_animal
from face_detect.face_detect import process_face_detection
from violance_detect.violation_detect import predict_violation
from meetup_detect.detect import extract_text_from_file, isPersonalDetails
from db.save_to_mysql import insert_attachment
from config import *  # REDIS_HOST, REDIS_PORT, REDIS_DB, NSFW_MODEL_DIR, VIDEO_SNAPSHOT_INTERVAL, etc.

# ────────── Redis setup ──────────
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
INPUT_QUEUE = "fliqz_moderation_image_video_queue"
OUTPUT_QUEUE = "processed_media_queue"

# ────────── NSFW Detector ──────────
nsfw_detector = NSFWDetector(NSFW_MODEL_DIR)

# ────────── Helper Functions ──────────
def detect_personal_info(data: dict):
    text_to_check = data.get("text", "")
    if "filename" in data:
        text_to_check += " " + extract_text_from_file(data["filename"])
    return isPersonalDetails(text_to_check)

def build_redis_json(file_path, minor, nsfw, animal, violation, personal_info, blur_applied=0):
    flagged_by_ai = minor and nsfw
    return {
        "id": str(uuid.uuid4()),
        "filename": file_path,
        "driver": 1,
        "type": "post",
        "user_id": None,
        "post_id": None,
        "story_id": None,
        "message_id": None,
        "collab_id": None,
        "coconut_id": None,
        "has_thumbnail": 0,
        "has_blurred_preview": 0,
        "payment_request_id": None,
        "blur_applied": int(blur_applied),
        "minor_detected": int(minor),
        "nsfw_detected": int(nsfw),
        "flagged_by_ai": int(flagged_by_ai),
        "animal_detected": int(animal),
        "violance_detected": int(violation),
        "is_personal_details_detected": int(personal_info),
        "is_reported": 0,
        "report_status": None,
        "report_create_date": None,
        "admin_verified_status": None,
        "moderator_notes": None,
        "is_deleted": 0
    }

def process_image(file_path, data_from_redis=None):
    print(f"\n🔍 Processing image: {file_path}")
    minor_detected = False
    nsfw_detected = False
    animal_detected = False
    violation_detected = False
    personal_info_detected = False

    # ── Animal detection
    try:
        found, animal_label = has_animal(file_path)
        animal_detected = found
        print(f"🐾 Animal detected: {animal_label}" if found else "✅ No animal detected")
    except Exception as e:
        print(f"❌ Animal detection error: {e}")

    # ── NSFW / Minor detection
    try:
        results = process_face_detection(file_path)
        nsfw_detected = results.get("is_nsfw", False)
        minor_detected = results.get("minor_detected", False)
        print(f"📊 NSFW detected: {nsfw_detected}, 👶 Minor detected: {minor_detected}")
    except Exception as e:
        print(f"❌ NSFW detection error: {e}")

    # ── Violence detection
    try:
        violation_pred = predict_violation(file_path, file_type='image')
        violation_detected = violation_pred[0]  # 1=violent
        print(f"⚔️ Violence detected: {violation_detected}, model value: {violation_pred[1]:.4f}")
    except Exception as e:
        print(f"❌ Violence detection error: {e}")

    # ── Personal info detection
    try:
        personal_info_detected = detect_personal_info(data_from_redis or {"filename": file_path})
        print(f"📄 Personal info detected: {personal_info_detected}")
    except Exception as e:
        print(f"❌ Personal info detection error: {e}")

    # ── Build JSON and push to Redis
    redis_json = build_redis_json(
        file_path,
        minor_detected,
        nsfw_detected,
        animal_detected,
        violation_detected,
        personal_info_detected,
        blur_applied=0
    )
    r.lpush(OUTPUT_QUEUE, json.dumps(redis_json))
    print(f"✅ JSON pushed to Redis:\n{json.dumps(redis_json, indent=2)}")

    # ── Insert into MySQL
    try:
        insert_attachment(redis_json)
        print("✅ Data inserted into MySQL successfully")
    except Exception as e:
        print(f"❌ MySQL insert error: {e}")

def process_video(video_path, data_from_redis=None):
    print(f"\n🎬 Processing video: {video_path}")
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        frame_interval = int(fps * VIDEO_SNAPSHOT_INTERVAL)
        count = 0
        snapshot_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if count % frame_interval == 0:
                snapshot_count += 1
                snapshot_file = f"{Path(video_path).stem}_snapshot_{snapshot_count}.jpg"
                temp_path = os.path.join("/tmp", snapshot_file)
                cv2.imwrite(temp_path, frame)
                process_image(temp_path, data_from_redis)
                os.remove(temp_path)
            count += 1
        cap.release()
        print(f"✅ Finished processing video: {video_path}")
    except Exception as e:
        print(f"❌ Video processing error: {e}")

# ────────── Worker Loop ──────────
def worker():
    print("🚀 Worker started. Waiting for files in Redis queue...")
    while True:
        item = r.brpop(INPUT_QUEUE, timeout=5)
        if item:
            _, json_data = item
            try:
                data = json.loads(json_data.decode())
                file_path = data.get("filename")
                if not file_path or not os.path.exists(file_path):
                    print(f"⚠️ File does not exist: {file_path}")
                    continue

                ext = Path(file_path).suffix.lower()
                if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                    process_image(file_path, data)
                elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                    process_video(file_path, data)
                else:
                    print(f"⚠️ Unsupported file type: {file_path}")

            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON: {json_data}")
        else:
            time.sleep(0.1)

if __name__ == "__main__":
    worker()
