import os
import time
import subprocess
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

                try:
                    subprocess.run(
                        ["python", face_detect_script, "--image", event.src_path],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error running face_detect.py: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "storage", "nonfilter")

    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    print(f"Watching folder: {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
