import os
import time
import subprocess
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                print("Image detected:", event.src_path)

                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                face_detect_script = os.path.join(base_dir, "face-detect", "face_detect.py")

                # Make a copy of the file into a temporary folder
                copied_dir = os.path.join(base_dir, "storage", "copied_images")
                os.makedirs(copied_dir, exist_ok=True)

                dest_path = os.path.join(copied_dir, os.path.basename(event.src_path))
                shutil.copy2(event.src_path, dest_path)
                print(f"Copied image to: {dest_path}")

                # Run detection on the copied file
                try:
                    subprocess.run(
                        ["python", face_detect_script, "--image", dest_path],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error running face_detect.py: {e}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Folders to watch
    watch_paths = [
        os.path.join(base_dir, "storage", "uploads", "advertisement"),
        os.path.join(base_dir, "storage", "uploads", "auction", "gallery"),
        os.path.join(base_dir, "storage", "uploads", "avatar"),
        os.path.join(base_dir, "storage", "uploads", "posts", "images"),
        os.path.join(base_dir, "storage", "uploads", "products", "gallery"),
    ]

    event_handler = MyHandler()
    observer = Observer()

    for path in watch_paths:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=False)
            print(f"Watching folder: {path}")
        else:
            print(f"Path does not exist: {path}")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
