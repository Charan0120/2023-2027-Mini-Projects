import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import time
import os

# Guard against duplicate initialization (firebase_admin raises if already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), "firebasekey.json"))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://edge-ai-based-threat-detection-default-rtdb.firebaseio.com/'
    })

last_push = 0
last_status = None

def send_to_firebase(person, weapon, confidence, status, node, location):
    global last_push, last_status

    current_time = time.time()

    if current_time - last_push > 2:
        data = {
            "node_id": node,
            "location": location,
            "person": person,
            "weapon": weapon,
            "confidence": confidence * 100,
            "status": status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            db.reference("live_status").set(data)

            if status != "SAFE" and status != last_status:
                db.reference("alerts").push(data)

            last_push = current_time
            last_status = status

        except Exception as e:
            print("Firebase Error:", e)