#This application performs live attention detection using your webcam. No images, videos, or personal data are stored or transmitted, unless you enable alert features like Telegram.



import cv2
import dlib
import numpy as np
import time
import requests
import pygetwindow as gw
import pygame

#Warning msg
print("🔒 NOTICE: This application monitors your eye activity and whether Zoom/Meet is your active window. No data is saved or shared beyond alerting the host.")


# ====== Telegram Bot Setup (HARDCODED) ======
BOT_TOKEN = "7811072771:AAE4pTdxDk9HzvO_gUChMJUpGNBM2GiN0-I"
CHAT_ID = "1061787113"  # Replace this with your actual chat ID

#To prevent spam messages
last_alert_time = 0
COOLDOWN_SECONDS = 5

def should_alert():
    global last_alert_time
    now = time.time()
    if now - last_alert_time >= COOLDOWN_SECONDS:
        last_alert_time = now
        return True
    return False

# ====== Sound Alert Setup ======
def play_notification_sound():
    try:
        pygame.mixer.init()
        pygame.mixer.music.load("ding.mp3")  # Replace with your file
        pygame.mixer.music.play()
        time.sleep(2)
    except Exception as e:
        print(f"🔇 Failed to play sound: {e}")


# ====== Window Monitoring ====== 
def is_zoom_or_meet_focused():
    active = gw.getActiveWindow()
    if active is None:
        return False
    return "Zoom" in active or "Meet" in active or "Google Meet" in active

def notify_host(student_name, reason="Student is distracted or inattentive."):
    text = f"🚨 ALERT: Student '{student_name}' is inattentive!\nReason: {reason}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    response = requests.post(url, data=payload)

    if response.status_code == 200:
        print("✅ Alert sent successfully!")
    else:
        print(f"❌ Failed to send alert. Error: {response.text}")

# ====== Eye Detection Setup ======
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

def eye_aspect_ratio(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

# ====== Constants ======

EYE_CLOSED_FRAMES = 10
NO_FACE_THRESHOLD = 10

# ====== Runtime Vars ======
closed_frames = 00
no_face_frames = 0
no_focus_frames = 0
eye_alert_sent = False
face_alert_sent = False
focus_alert_sent = False

WINDOW_UNFOCUSED_THRESHOLD = 25  # e.g. 10 frames = approx 10 seconds
no_focus_frames = 0

#To calibrate the EAR according to the user's face structure.
def calibrate_ear(cap, detector, predictor, calibration_time=5):
    print("🔧 Calibrating eye detection... please look directly at the camera.")
    start_time = time.time()
    ear_values = []

    while time.time() - start_time < calibration_time:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)

        if len(faces) == 0:
            continue

        largest_face = max(faces, key=lambda rect: rect.width() * rect.height())
        landmarks = predictor(gray, largest_face)

        left_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(36, 42)])
        right_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(42, 48)])

        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        ear_values.append(avg_ear)

    if len(ear_values) == 0:
        print("⚠️ Calibration failed. Using default EAR threshold.")
        return 0.25  # default

    personalized_threshold = np.mean(ear_values) * 0.75  # 75% of average open-eye EAR
    print(f"✅ EAR calibrated. Threshold set to {personalized_threshold:.3f}")
    return personalized_threshold


# ====== Student Login ======
student_name = "Atharva"

cap = cv2.VideoCapture(0)
EYE_AR_THRESHOLD = calibrate_ear(cap, detector, predictor)

print("👀 Eye-tracking started... press 'Q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    if len(faces) == 0:
        no_face_frames += 1
        closed_frames = 0  # Reset eye logic if no face
        print(f"Face not detected for {no_face_frames} frames")
        if no_face_frames >= NO_FACE_THRESHOLD and not face_alert_sent and should_alert():
            notify_host(student_name, reason="No face detected for a long time.")
            play_notification_sound()
            face_alert_sent = True
    else:
        no_face_frames = 0
        face_alert_sent = False

        # Face detected → process it
        largest_face = max(faces, key=lambda rect: rect.width() * rect.height())
        landmarks = predictor(gray, largest_face)

        left_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(36, 42)])
        right_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(42, 48)])

        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0

        # EYE CLOSED LOGIC (OUTSIDE of face detection)
        if avg_ear < EYE_AR_THRESHOLD:
            closed_frames += 1
            print(f"Eyes closed for {closed_frames} frames")
            if closed_frames >= EYE_CLOSED_FRAMES and not eye_alert_sent and should_alert():
                notify_host(student_name, reason="Eyes closed / sleeping / not attentive.")
                play_notification_sound()
                eye_alert_sent = True
        else:
            closed_frames = 0
            eye_alert_sent = False

    # ZOOM/MEET FOCUS CHECK
    if not is_zoom_or_meet_focused():
        no_focus_frames += 1
        print(f"Zoom/Meet not active for {no_focus_frames} frames")
        if no_focus_frames >= WINDOW_UNFOCUSED_THRESHOLD and not focus_alert_sent and should_alert():
            notify_host(student_name, reason="Zoom/Meet window not in focus")
            play_notification_sound()
            focus_alert_sent = True
    else:
        no_focus_frames = 0
        focus_alert_sent = False

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

