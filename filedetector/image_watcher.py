import os
import time
import sys
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

sys.path.append(str(Path(__file__).resolve().parent.parent))
# Import from db folder
from db.dbConfig import get_connection
from db.nsfw_detector import NSFWDetector

BASE_URL = "http://localhost:8000/images"
IMAGES_DIR = str(Path(__file__).parent.parent / "storage" / "filter" / "minor" / "nonfilter")
MODEL_PATH = str(Path(__file__).parent.parent / "mobilenet_v2_140_224")
THRESHOLD = 0.8 

class ImageHandler(FileSystemEventHandler):
    def __init__(self):
        self.detector = NSFWDetector(MODEL_PATH)
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith((".png", ".jpg", ".jpeg")):
            print(f"\nFile Detected: {event.src_path}")
            self.process_image(event.src_path)

    def process_image(self, image_path):
        print(f"Processing new image: {os.path.basename(image_path)}")
        
        try:
            result = self.detector.predict(image_path, THRESHOLD)
            
            if result.get('error'):
                print(f"Detection error: {result['error']}")
                return

            print("\nDetection Results:")
            for label, score in result["scores"].items():
                print(f"{label.upper()+':':<8} {score:.2f}%")
            print(f"NSFW: {'YES' if result['is_nsfw'] else 'NO'}")

            self.save_to_db(image_path, result)

            scores = result["scores"]
            top_label = max(scores, key=scores.get)

            base_minor_path = Path(__file__).parent.parent / "storage" / "filter" / "minor" / "filter"

            if top_label == "natural":
                dest_dir = base_minor_path / "minornonnsfw"
            elif top_label == "porn":
                dest_dir = base_minor_path / "minornsfw" / "porn"
            elif top_label == "sexy":
                dest_dir = base_minor_path / "minornsfw" / "sexy"
            else:
                dest_dir = None

            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = dest_dir / os.path.basename(image_path)
                shutil.move(image_path, dest_path)
                print(f"Moved {os.path.basename(image_path)} to {dest_path}")

        except Exception as e:
            print(f"Processing failed: {str(e)}")
    def save_to_db(self, image_path, result):
        try:
            conn = get_connection()
            if not conn:
                print("Database connection failed")
                return

            cursor = conn.cursor()
            
            sql = """INSERT INTO moderation_posts 
                     (file_url, file_type, nsfw_hentai, nsfw_porn, nsfw_sexy, flagged_by_ai, created_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            
            values = (
                f"{BASE_URL}/{os.path.basename(image_path)}",
                'image',
                float(result["scores"].get("hentai", 0)),
                float(result["scores"].get("porn", 0)),
                float(result["scores"].get("sexy", 0)),
                1 if result["is_nsfw"] else 0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            cursor.execute(sql, values)
            conn.commit()
            print("Saved to database")
            
        except Exception as e:
            print(f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print(f"Created images directory at {IMAGES_DIR}")

    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        exit(1)

    # Start watcher
    print(f"\nStarting image watcher on: {IMAGES_DIR}")
    print(f"Using model: {MODEL_PATH}")
    print(f"NSFW Threshold: {THRESHOLD*100}%")
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
