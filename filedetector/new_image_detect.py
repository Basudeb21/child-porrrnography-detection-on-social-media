import os
import sys
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Fix the import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "animal_detect"))
sys.path.append(BASE_DIR)  # Add project root to path

from animal_porn_detect import has_animal

# Import face processor with correct path
face_processor_path = os.path.join(BASE_DIR, "face-detect")
sys.path.append(face_processor_path)

try:
    from face_processor import process_face_detection
    print("✅ Face processor imported successfully")
except ImportError as e:
    print(f"❌ Failed to import face_processor: {e}")
    print(f"🔍 Looking in: {face_processor_path}")
    # List files in face-detect directory to debug
    if os.path.exists(face_processor_path):
        print(f"📁 Files in face-detect: {os.listdir(face_processor_path)}")
    process_face_detection = None

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                print("Image detected:", event.src_path)

                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                copied_dir = os.path.join(base_dir, "storage", "copied_images")
                os.makedirs(copied_dir, exist_ok=True)

                dest_path = os.path.join(copied_dir, os.path.basename(event.src_path))
                shutil.copy2(event.src_path, dest_path)
                print(f"Copied image to: {dest_path}")

                # 1. FIRST: Run animal detection on the COPIED file
                try:
                    found, animal = has_animal(dest_path)
                    if found:
                        print(f"🐾 Animal detected: {animal}")
                    else:
                        print("✅ No animal detected")
                except Exception as e:
                    print(f"❌ Error running animal detection: {e}")

                # 2. THEN: Run face detection (this will also run NSFW detection)
                if process_face_detection:
                    try:
                        print("🔍 Starting face and NSFW detection...")
                        results = process_face_detection(dest_path)
                        print("✅ Face detection completed successfully")
                        
                        # Log the results
                        if results:
                            print(f"📊 Detection Summary:")
                            print(f"   - Faces detected: {results.get('faces_detected', 0)}")
                            print(f"   - Minor detected: {results.get('minor_detected', False)}")
                            print(f"   - NSFW detected: {results.get('is_nsfw', False)}")
                            
                    except Exception as e:
                        print(f"❌ Error running face detection: {e}")
                else:
                    print("❌ Face processor not available, skipping face detection")

                # 3. Clean up the copied file after processing
                try:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                        print(f"🗑️ Cleaned up copied image: {dest_path}")
                except Exception as e:
                    print(f"❌ Error cleaning up: {e}")

def create_directories(paths):
    """Create directories if they don't exist"""
    for path in paths:
        os.makedirs(path, exist_ok=True)
        print(f"Created/verified directory: {path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    watch_paths = [
        os.path.join(base_dir, "storage", "uploads", "advertisement"),
        os.path.join(base_dir, "storage", "uploads", "auction", "gallery"),
        os.path.join(base_dir, "storage", "uploads", "avatar"),
        os.path.join(base_dir, "storage", "uploads", "posts", "images"),
        os.path.join(base_dir, "storage", "uploads", "products", "gallery"),
    ]

    # Create all directories
    create_directories(watch_paths)
    
    # Also create the copied_images directory
    copied_dir = os.path.join(base_dir, "storage", "copied_images")
    os.makedirs(copied_dir, exist_ok=True)
    print(f"Created/verified directory: {copied_dir}")

    event_handler = MyHandler()
    observer = Observer()

    for path in watch_paths:
        observer.schedule(event_handler, path, recursive=False)
        print(f"👀 Watching folder: {path}")

    observer.start()
    print("🚀 File watcher started. Waiting for images...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("🛑 File watcher stopped.")
    observer.join()