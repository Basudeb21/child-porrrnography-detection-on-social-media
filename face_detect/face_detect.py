import os
import cv2
import argparse
from nsfw.nsfw_detector import NSFWDetector
from animal_detect.animal_porn_detect import has_animal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--image', help='Path to image file')
args = parser.parse_args()

# Load models with absolute paths
faceProto = os.path.join(BASE_DIR, "opencv_face_detector.pbtxt")
faceModel = os.path.join(BASE_DIR, "opencv_face_detector_uint8.pb")
ageProto = os.path.join(BASE_DIR, "age_deploy.prototxt")
ageModel = os.path.join(BASE_DIR, "age_net.caffemodel")
genderProto = os.path.join(BASE_DIR, "gender_deploy.prototxt")
genderModel = os.path.join(BASE_DIR, "gender_net.caffemodel")

faceNet = cv2.dnn.readNet(faceModel, faceProto)
ageNet = cv2.dnn.readNet(ageModel, ageProto)
genderNet = cv2.dnn.readNet(genderModel, genderProto)

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
ageList = ['(0-2)', '(4-6)', '(8-12)', '(15-20)',
           '(25-32)', '(38-43)', '(48-53)', '(60-100)']
genderList = ['Male', 'Female']

padding = 20

# Initialize NSFW detector
nsfw_detector = NSFWDetector()

def highlightFace(net, frame, conf_threshold=0.7):
    frameOpencvDnn = frame.copy()
    frameHeight, frameWidth = frameOpencvDnn.shape[:2]
    blob = cv2.dnn.blobFromImage(frameOpencvDnn, 1.0, (300, 300),
                                 [104, 117, 123], swapRB=False)
    net.setInput(blob)
    detections = net.forward()
    faceBoxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            x1 = int(detections[0, 0, i, 3] * frameWidth)
            y1 = int(detections[0, 0, i, 4] * frameHeight)
            x2 = int(detections[0, 0, i, 5] * frameWidth)
            y2 = int(detections[0, 0, i, 6] * frameHeight)
            faceBoxes.append([x1, y1, x2, y2])
    return faceBoxes

def detect_minor(frame):
    faceBoxes = highlightFace(faceNet, frame)
    minor_detected = False
    for faceBox in faceBoxes:
        face = frame[max(0, faceBox[1]-padding):min(faceBox[3]+padding, frame.shape[0]-1),
                     max(0, faceBox[0]-padding):min(faceBox[2]+padding, frame.shape[1]-1)]
        blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227),
                                     MODEL_MEAN_VALUES, swapRB=False)
        ageNet.setInput(blob)
        agePreds = ageNet.forward()
        age = ageList[agePreds[0].argmax()]
        min_age = int(age.strip("()").split("-")[0])
        if min_age < 18:
            minor_detected = True
    return minor_detected

def detect_nsfw(image_path):
    result = nsfw_detector.predict(image_path)
    return result.get("is_nsfw", False)

def detect_animal(image_path):
    found, _ = has_animal(image_path)
    return found

def analyze_image(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Cannot read image {image_path}")

    minor_detected = detect_minor(frame)
    nsfw_detected = detect_nsfw(image_path)
    animal_detected = detect_animal(image_path)
    flagged_by_ai = minor_detected and nsfw_detected

    return {
        "filename": image_path,
        "minor_detected": minor_detected,
        "nsfw_detected": nsfw_detected,
        "animal_detected": animal_detected,
        "flagged_by_ai": flagged_by_ai
    }

# ✅ Wrapper expected by worker.py
def process_face_detection(image_path):
    result = analyze_image(image_path)
    return {
        "minor_detected": result["minor_detected"],
        "is_nsfw": result["nsfw_detected"]
    }

if __name__ == "__main__":
    if args.image:
        print(analyze_image(args.image))
