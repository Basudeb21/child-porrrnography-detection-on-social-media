# animal_porn_detect.py

from ultralytics import YOLO
import os

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load YOLOv8 pre-trained model with correct path
model_path = os.path.join(SCRIPT_DIR, "yolov8n.pt")
model = YOLO(model_path)

ANIMAL_CLASSES = [
    "bird", "cat", "dog", "horse", "sheep", 
    "cow", "elephant", "bear", "zebra", 
    "giraffe", "mouse"
]

def has_animal(image_path):
    # Make sure the image path is absolute
    if not os.path.isabs(image_path):
        image_path = os.path.abspath(image_path)
    
    results = model(image_path)
    
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            if label in ANIMAL_CLASSES:
                return True, label
    return False, None
