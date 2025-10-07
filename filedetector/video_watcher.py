import os
import cv2
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Where videos will be uploaded
VIDEO_DIR = str(Path(__file__).parent.parent / "storage" / "uploads" / "videos")
# Where to dump snapshots for NSFW detection
SNAPSHOT_DIR = str(Path(__file__).parent.parent / "storage" / "filter" / "minor" / "nonfilter")

INTERVAL = 10  # seconds

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            return

        print(f"\n[VIDEO] Detected new video: {event.src_path}")
        self.process_video(event.src_path)

    def process_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_interval = fps * INTERVAL
        count = 0
        snapshot_count = 0

        os.makedirs(SNAPSHOT_DIR, exist_ok=True)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if count % frame_interval == 0:
                snapshot_count += 1
                filename = os.path.join(
                    SNAPSHOT_DIR,
                    f"{Path(video_path).stem}_snapshot_{snapshot_count}.jpg"
                )
                cv2.imwrite(filename, frame)
                print(f"[VIDEO] Saved snapshot: {filename}")
            count += 1

        cap.release()
        print(f"[VIDEO] Finished processing {video_path}")

if __name__ == "__main__":
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, VIDEO_DIR, recursive=False)
    observer.start()

    print(f"Watching for videos in {VIDEO_DIR} ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
