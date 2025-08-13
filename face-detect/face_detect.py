import os
import cv2
import math
import argparse
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NSFW_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))  
STORAGE_BASE = os.path.join(NSFW_ROOT, "storage", "filter")

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

# Load networks
faceNet = cv2.dnn.readNet(faceModel, faceProto)
ageNet = cv2.dnn.readNet(ageModel, ageProto)
genderNet = cv2.dnn.readNet(genderModel, genderProto)

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
ageList = ['(0-2)', '(4-6)', '(8-12)', '(15-20)',
           '(25-32)', '(38-43)', '(48-53)', '(60-100)']
genderList = ['Male', 'Female']

def highlightFace(net, frame, conf_threshold=0.7):
    frameOpencvDnn = frame.copy()
    frameHeight = frameOpencvDnn.shape[0]
    frameWidth = frameOpencvDnn.shape[1]
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

    return frameOpencvDnn, faceBoxes

def move_based_on_age(image_path, age):
    """Move file into minor or adult folder based on predicted age."""
    minor_folder = os.path.join(STORAGE_BASE, "minor", "nonfilter")
    adult_folder = os.path.join(STORAGE_BASE, "adult")

    os.makedirs(minor_folder, exist_ok=True)
    os.makedirs(adult_folder, exist_ok=True)

    # Extract numeric range from age string
    min_age = int(age.strip("()").split("-")[0])

    if min_age < 18:
        dest_folder = minor_folder
    else:
        dest_folder = adult_folder

    dest_path = os.path.join(dest_folder, os.path.basename(image_path))
    shutil.move(image_path, dest_path)
    print(f"Moved file to: {dest_path}")

padding = 20

# --- Static Image Mode ---
if args.image:
    frame = cv2.imread(args.image)
    if frame is None:
        print(f"Could not load image: {args.image}")
        exit()

    resultImg, faceBoxes = highlightFace(faceNet, frame)
    if not faceBoxes:
        print("No face detected")
    else:
        move_to_minor = False  

        for faceBox in faceBoxes:
            face = frame[max(0, faceBox[1] - padding):
                         min(faceBox[3] + padding, frame.shape[0] - 1),
                         max(0, faceBox[0] - padding):
                         min(faceBox[2] + padding, frame.shape[1] - 1)]

            blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227),
                                         MODEL_MEAN_VALUES, swapRB=False)
            genderNet.setInput(blob)
            genderPreds = genderNet.forward()
            gender = genderList[genderPreds[0].argmax()]

            ageNet.setInput(blob)
            agePreds = ageNet.forward()
            age = ageList[agePreds[0].argmax()]

            print(f'Gender: {gender}, Age: {age}')

            # If any detected face is under 18, mark for minor folder
            min_age = int(age.strip("()").split("-")[0])
            if min_age < 18:
                move_to_minor = True

        # After checking all faces, move file only once
        if move_to_minor:
            dest_folder = os.path.join(STORAGE_BASE, "minor", "nonfilter")
        else:
            dest_folder = os.path.join(STORAGE_BASE, "adult")

        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, os.path.basename(args.image))
        shutil.move(args.image, dest_path)
        print(f"Moved file to: {dest_path}")
