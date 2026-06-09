**Team Members**
# B.Charan 2451-23-749-001
# G.Siddartha 2451-23-749-303
# N.Vikas 2451-23-749-031

# AI-Based Smart Surveillance System 

An end-to-end, real-time AI surveillance system that uses an **ESP32 Camera** to stream video over WebSockets to a **Python server**, which processes the frames using **YOLOv8** for weapon detection and **Face Recognition** for unauthorized person detection. 

The system includes a beautiful, futuristic web dashboard with role-based access control (Admin/Operator) backed by **Firebase Realtime Database**.

---

##  Features
- **Hardware Integration:** Real-time low-latency video streaming from an ESP32-CAM via WebSockets.
- **Weapon Detection:** Uses a custom-trained YOLOv8 model (`best1.pt`) to instantly detect dangerous objects (e.g., guns, knives).
- **Face Recognition:** Compares live faces against an `authorized/` database directory.
- **Threat Logic:** Automatically classifies situations as `SAFE`, `UNAUTHORIZED`, `WEAPON_DETECTED`, or `HIGH_THREAT`.
- **Role-Based Web UI:** 
  - **Admin Dashboard:** View live feeds, upload new authorized faces directly from the browser, and manage cameras/users.
  - **Operator Dashboard:** A locked-down view for monitoring a specific camera node.
- **Cloud Database:** Stores encrypted user credentials (SHA-256) and roles in Firebase.
- **Internet Ready:** Designed to work over public internet tunneling (like Ngrok) so you can monitor your home from your phone on 5G.

---

##  Hardware Requirements
1. **ESP32-CAM Module** (AI-Thinker model recommended)
2. FTDI Programmer (to upload code to the ESP32)
3. A Windows/Mac/Linux Laptop (acts as the AI Server)
4. A 2.4GHz WiFi connection (ESP32 does not support 5GHz)

---

##  Software Prerequisites
Before you begin, ensure you have the following installed on your laptop:
- **Python 3.9 - 3.11** (Do not use 3.12+ as some ML libraries may have conflicts)
- **Git**
- **Arduino IDE** (for flashing the ESP32)

### Python Dependencies
You will need to install the following libraries via `pip`:
```bash
pip install flask websockets opencv-python numpy ultralytics face_recognition dlib firebase-admin
```
*(Note: Installing `dlib` and `face_recognition` on Windows usually requires installing Visual Studio C++ Build Tools first).*

---

##  Setup & Installation (Step-by-Step)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Charan0120/Ai-Based-Smart-Surveillance-System.git
cd Ai-Based-Smart-Surveillance-System
```

### Step 2: Set up Firebase (Database & Auth)
1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2. Create a **Realtime Database** and set the rules to allow read/write for authenticated users (or open for testing, though not recommended).
3. Go to **Project Settings > Service Accounts** and generate a new private key.
4. Download the JSON file, rename it to `firebasekey.json`, and place it in the root folder of this project.
5. Open `firebase_config.py` and update the `databaseURL` to match your Firebase database URL.

### Step 3: Configure the ESP32 Camera
1. Open the Arduino IDE.
2. Open the file located at `live/weblive/weblive.ino`.
3. Change **Line 6 & 7** to match your local WiFi name and password:
   ```cpp
   const char* ssid = "YOUR_WIFI_NAME";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
4. Open your laptop's Command Prompt, type `ipconfig`, and find your IPv4 Address.
5. Change **Line 11** to match your laptop's IP address:
   ```cpp
   const char* server_ip = "192.168.x.x";
   ```
6. Connect the ESP32 to your laptop via the FTDI programmer and hit **Upload**.

---

##  Running the System

### 1. Start the Server
Open a terminal in the project folder and run:
```bash
python app.py
```
*Wait for the console to say "WebSocket running" and "Flask running on http://0.0.0.0:5000".*

### 2. Power the ESP32
Plug the ESP32 into power. It will connect to your WiFi and establish a WebSocket connection to your laptop. The terminal will print ` ESP32 Connected`.

### 3. Open the Dashboard
Open your web browser and navigate to:
```
http://localhost:5000
```
- **Default Admin Login:** `admin` / `admin123`
- From here, you can watch the live feed and upload new authorized faces.

---

##  Exposing to the Internet (Ngrok)
If you want to view the dashboard on your phone while away from home:
1. Download [Ngrok](https://ngrok.com/).
2. Authenticate: `ngrok config add-authtoken <your-token>`
3. Run the tunnel:
   ```bash
   ngrok http 5000
   ```
4. Copy the `https://...ngrok-free.app` link and open it on your phone!

---

##  Project Architecture Breakdown

- **`app.py`**: The Flask Web Server. Handles HTTP routing, serves the dashboard, handles photo uploads, and starts the WebSocket server in the background.
- **`websocket_server.py`**: Listens on Port 8765. Receives raw JPEG frames from the ESP32 and stores them in memory.
- **`detector.py`**: The AI Engine. Runs continuously in a background thread. Grabs frames, runs YOLOv8 and Face Recognition, and outputs the threat status.
- **`globals.py`**: Shared memory variables (frames, threat status) allowing the Web Server, WebSocket Server, and AI Engine to communicate instantly.
- **`auth_firebase.py`**: Handles secure SHA-256 password hashing and talks to Firebase to verify logins.
- **`best1.pt`**: The custom-trained YOLOv8 neural network weights for weapon detection.
- **`authorized/`**: Directory where uploaded photos of allowed personnel are saved.
- **`live/weblive/weblive.ino`**: The C++ firmware running on the ESP32.

---

##  Security Note
**Never upload your `firebasekey.json` to GitHub!** This repository includes a `.gitignore` file specifically designed to block this file from being pushed. If you deploy this to a cloud VPS, you must manually transfer the JSON key to the server.
