import cv2
import face_recognition
import os
import numpy as np
from ultralytics import YOLO
from config import MODEL_PATH, CONF_THRESHOLD
import globals

# Absolute path — same result whether imported from app.py or run directly
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
AUTHORIZED_FOLDER = os.path.join(BASE_DIR, "authorized")

print(f"[Detector] AUTHORIZED_FOLDER = {AUTHORIZED_FOLDER}")

model = YOLO(MODEL_PATH)

known_encodings = []
known_names     = []


def reload_encodings(folder=None):
    """
    Scan `folder` (defaults to AUTHORIZED_FOLDER) and rebuild
    known_encodings / known_names.  Safe to call at any time.
    Returns the list of loaded names.
    """
    global known_encodings, known_names

    if folder is None:
        folder = AUTHORIZED_FOLDER

    new_encodings = []
    new_names     = []

    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
        print(f"[Detector] Created folder: {folder}")

    image_files = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")
    ]
    print(f"[Detector] Scanning {len(image_files)} image(s) in {folder}")

    for fname in image_files:
        path = os.path.join(folder, fname)
        try:
            img = face_recognition.load_image_file(path)
            enc = face_recognition.face_encodings(img)
            if enc:
                new_encodings.append(enc[0])
                new_names.append(os.path.splitext(fname)[0].replace("_", " "))
                print(f"[Detector]  ✓ Encoded: {fname}")
            else:
                print(f"[Detector]  ⚠ No face found in: {fname}")
        except Exception as e:
            print(f"[Detector]  ✗ Error encoding {fname}: {e}")

    known_encodings = new_encodings
    known_names     = new_names
    globals.known_names_count = len(known_names)
    print(f"[Detector] Reload done. Authorized: {known_names}")
    return known_names


# Load on startup
reload_encodings()


def process_frame(frame, frame_count):
    h, w, _ = frame.shape
    globals.current_boxes = []

    # ── FACE RECOGNITION ──────────────────────────────────────────────────────
    unauthorized         = False
    globals.current_person = None

    small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    faces     = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, faces)

    for (top, right, bottom, left), enc in zip(faces, encodings):
        name = "UNAUTHORIZED"
        conf = 0.5

        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, enc)
            best_idx  = int(np.argmin(distances))
            best_dist = float(distances[best_idx])
            if best_dist < 0.5:
                name = known_names[best_idx]
                conf = round(1.0 - best_dist, 2)
            else:
                unauthorized = True
        else:
            unauthorized = True

        globals.current_person = name
        top *= 2; right *= 2; bottom *= 2; left *= 2

        globals.current_boxes.append({
            "type":       "face",
            "label":      name,
            "x":          left / w,
            "y":          top  / h,
            "w":          (right - left) / w,
            "h":          (bottom - top) / h,
            "confidence": conf,
        })

    # ── YOLO WEAPON DETECTION ─────────────────────────────────────────────────
    weapon_detected        = False
    globals.current_weapon     = None
    globals.current_confidence = 0

    results = model(frame, verbose=False)

    for r in results:
        for box in r.boxes:
            cls   = int(box.cls[0])
            label = model.names[cls]
            conf  = float(box.conf[0])

            if conf > CONF_THRESHOLD:
                weapon_detected            = True
                globals.current_weapon     = label
                globals.current_confidence = conf
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                globals.current_boxes.append({
                    "type":       "weapon",
                    "label":      label,
                    "x":          x1 / w,
                    "y":          y1 / h,
                    "w":          (x2 - x1) / w,
                    "h":          (y2 - y1) / h,
                    "confidence": conf,
                })

    # ── THREAT STATUS ─────────────────────────────────────────────────────────
    if weapon_detected and unauthorized:
        globals.threat_status = "HIGH_THREAT"
    elif weapon_detected:
        globals.threat_status = "WEAPON_DETECTED"
    elif unauthorized:
        globals.threat_status = "UNAUTHORIZED"
    else:
        globals.threat_status = "SAFE"