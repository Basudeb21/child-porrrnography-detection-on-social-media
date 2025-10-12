# run_all_watchers.py
import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PATH = BASE_DIR.parent / ".venv" / "bin" / "activate"
 

scripts = [
    ("Image Watcher", BASE_DIR / "image_watcher.py"),
    ("New Image Detect", BASE_DIR / "new_image_detect.py"),
    ("Video Watcher", BASE_DIR / "video_watcher.py"),
]

def run_in_new_terminal(title, script_path):
    """
    Launches a script in a new macOS Terminal window with venv activated
    """
    if not VENV_PATH.exists():
        print(f" Virtual environment not found at {VENV_PATH}")
        return

    command = (
        f'osascript -e \'tell application "Terminal" '
        f'to do script "cd {BASE_DIR} && source {VENV_PATH} && python3 {script_path}"\''
    )

    subprocess.Popen(command, shell=True)
    print(f"Launched {title} in new Terminal window (with venv).")

if __name__ == "__main__":
    print("Launching all watchers with virtual environment...\n")

    for name, script in scripts:
        if not script.exists():
            print(f"Error: {script} not found.")
        else:
            run_in_new_terminal(name, script)
            time.sleep(1)

    print("\nAll watchers started successfully!")
