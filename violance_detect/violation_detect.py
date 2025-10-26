import os
import cv2
import numpy as np
from tensorflow.keras.models import load_model

# Load model once
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model/MobBiLSTM_model_saved101.keras")
model = load_model(MODEL_PATH)

FRAME_SIZE = (64, 64)
FRAMES_PER_CLIP = 16

def preprocess_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, FRAME_SIZE)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
    cap.release()

    if len(frames) == 0:
        raise ValueError(f"No frames in video: {video_path}")

    if len(frames) < FRAMES_PER_CLIP:
        frames.extend([frames[-1]] * (FRAMES_PER_CLIP - len(frames)))
    else:
        frames = frames[:FRAMES_PER_CLIP]

    frames = np.array(frames) / 255.0
    return np.expand_dims(frames, axis=0)

def preprocess_image(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Image not found: {image_path}")
    frame = cv2.resize(frame, FRAME_SIZE)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frames = np.array([frame] * FRAMES_PER_CLIP) / 255.0
    return np.expand_dims(frames, axis=0)

def predict_violation(file_path, file_type='video'):
    if file_type == 'video':
        clip = preprocess_video(file_path)
    else:
        clip = preprocess_image(file_path)
    prediction = model.predict(clip)[0][0]
    # 1 = violent, 0 = non-violent
    return int(prediction < 0.5), float(prediction)
