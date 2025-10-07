# new_image_detect.py
import os
import sys
import time
import subprocess
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Fix the import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "animal_detect"))

from animal_porn_detect import has_animal

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                print("Image detected:", event.src_path)

                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                face_detect_script = os.path.join(base_dir, "face-detect", "face_detect.py")
                copied_dir = os.path.join(base_dir, "storage", "copied_images")
                os.makedirs(copied_dir, exist_ok=True)

                dest_path = os.path.join(copied_dir, os.path.basename(event.src_path))
                shutil.copy2(event.src_path, dest_path)
                print(f"Copied image to: {dest_path}")

                try:
                    subprocess.run(
                        ["python", face_detect_script, "--image", dest_path],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error running face_detect.py: {e}")

                try:
                    found, animal = has_animal(dest_path)
                    if found:
                        print(f"Animal detected in image: {animal}")
                    else:
                        print("No animal detected in image")
                except Exception as e:
                    print(f"Error running animal detection: {e}")

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
        os.path.join(base_dir, "storage", "filter", "minor", "nonfilter"),
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
        print(f"Watching folder: {path}")

    observer.start()
    print("File watcher started. Waiting for images...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("File watcher stopped.")
    observer.join()