import asyncio
import websockets
import numpy as np
import cv2
import queue
import globals
from detector import process_frame
#from firebase_service import send_to_firebase
from config import *

frame_queue = queue.Queue(maxsize=3)

async def websocket_handler(websocket):
    print("✅ ESP32 Connected")

    try:
        while True:
            data = await websocket.recv()
            frame = cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)

            if frame is None:
                continue

            globals.frame_global = frame

            if not frame_queue.full():
                frame_queue.put(frame)

    except Exception as e:
        print("WebSocket Error:", e)

    finally:
        print("❌ ESP32 Disconnected")

def process_loop():
    frame_count = 0

    while True:
        if frame_queue.empty():
            continue

        frame = frame_queue.get()
        frame_count += 1

        if frame_count % 5 != 0:
            continue

        process_frame(frame, frame_count)

        '''send_to_firebase(
            globals.current_person,
            globals.current_weapon,
            globals.current_confidence,
            globals.threat_status,
            NODE_ID,
            LOCATION
        )'''

async def start_websocket():
    server = await websockets.serve(
        websocket_handler,
        "0.0.0.0",
        8765,
        ping_interval=20,
        ping_timeout=20
    )
    print("🚀 WebSocket running")
    await asyncio.Future()