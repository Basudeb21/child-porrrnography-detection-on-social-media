import redis
import time
import os
from pathlib import Path
import cv2
import uuid
import json

from animal_detect.animal_porn_detect import has_animal
from nsfw.nsfw_detector import NSFWDetector
from face_detect.face_detect import process_face_detection
from config import *  # Make sure NSFW_MODEL_DIR, MYSQL_*, REDIS_* are here
from db.save_to_mysql import insert_attachment  # Your MySQL insert function

# Initialize NSFW detector
detector = NSFWDetector(NSFW_MODEL_DIR)

# Redis connection
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Queue names
INPUT_QUEUE = "fliqz_moderation_image_video_queue"
OUTPUT_QUEUE = "processed_media_queue"


def build_redis_json(file_path, minor_detected, nsfw_detected, animal_detected):
    flagged_by_ai = minor_detected and nsfw_detected

    return {
        "id": str(uuid.uuid4()),
        "filename": file_path,  # Full path from Redis
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
        "is_personal_details_detected": 0,
        "blur_applied": 0,
        "minor_detected": int(minor_detected),
        "nsfw_detected": int(nsfw_detected),
        "flagged_by_ai": int(flagged_by_ai),
        "animal_detected": int(animal_detected),
        "is_reported": 0,
        "report_status": None,
        "report_create_date": None,
        "admin_verified_status": None,
        "moderator_notes": None,
        "is_deleted": 0
    }


def process_image(file_path: str):
    print(f"\n🔍 Processing image: {file_path}")

    minor_detected = False
    nsfw_detected = False
    animal_detected = False

    # Animal detection
    try:
        found, animal = has_animal(file_path)
        animal_detected = found
        print(f"🐾 Animal detected: {animal}" if found else "✅ No animal detected")
    except Exception as e:
        print(f"❌ Animal detection error: {e}")

    # NSFW / minor detection
    try:
        results = process_face_detection(file_path)
        nsfw_detected = results.get("is_nsfw", False)
        minor_detected = results.get("minor_detected", False)
        print(f"📊 NSFW detected: {nsfw_detected}")
        print(f"👶 Minor detected: {minor_detected}")
        print(f"🤖 Flagged by AI: {nsfw_detected and minor_detected}")
    except Exception as e:
        print(f"❌ NSFW detection error: {e}")

    # Build JSON
    redis_json = build_redis_json(file_path, minor_detected, nsfw_detected, animal_detected)

    # Push to Redis output queue
    r.lpush(OUTPUT_QUEUE, json.dumps(redis_json))
    print(f"✅ JSON pushed to Redis:\n{json.dumps(redis_json, indent=2)}")

    # Insert into MySQL
    try:
        insert_attachment(redis_json)
        print("✅ Data inserted into MySQL successfully")
    except Exception as e:
        print(f"❌ MySQL insert error: {e}")


def process_video(video_path: str):
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
                print(f"📸 Snapshot saved: {temp_path}")
                process_image(temp_path)
                os.remove(temp_path)

            count += 1

        cap.release()
        print(f"✅ Finished processing video: {video_path}")

    except Exception as e:
        print(f"❌ Video processing error: {e}")


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

                # Detect file type
                ext = Path(file_path).suffix.lower()
                if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                    process_image(file_path)
                elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                    process_video(file_path)
                else:
                    print(f"⚠️ Unsupported file type: {file_path}")

            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON: {json_data}")
        else:
            time.sleep(0.1)


if __name__ == "__main__":
    worker()
