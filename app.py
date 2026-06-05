import os
import time
import threading
import asyncio
import traceback
from functools import wraps

import cv2
from flask import (
    Flask, Response, jsonify, render_template,
    request, redirect, session, url_for
)

# ── Absolute paths (works regardless of CWD) ─────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
AUTHORIZED_FOLDER = os.path.join(BASE_DIR, "authorized")
os.makedirs(AUTHORIZED_FOLDER, exist_ok=True)

print(f"[INFO] AUTHORIZED_FOLDER = {AUTHORIZED_FOLDER}")

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "surv-ai-secret-2024")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# ── Project imports (after paths are set) ────────────────────────────────────
from websocket_server import start_websocket, process_loop
import globals
from auth_firebase import verify_user, create_user, delete_user, get_all_users
from config import NODE_ID, LOCATION

# detector must be imported last — it calls reload_encodings() at import time
import detector


# ── Helpers ───────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ok, role, node_id, location = verify_user(username, password)
        if ok:
            session["user"]     = username
            session["role"]     = role
            session["node_id"]  = node_id
            session["location"] = location
            return redirect(url_for("index"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Role-based redirect ───────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("user_dashboard"))


# ── Dashboards ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("user_dashboard"))
    return render_template("surveillance_dashboard.html",
                           username=session["user"])


@app.route("/user_dashboard")
@login_required
def user_dashboard():
    return render_template("user_dashboard.html",
                           username=session["user"],
                           node_id=session.get("node_id", "NODE-A1"),
                           location=session.get("location", "Main Entrance"))


# ── Video feed ────────────────────────────────────────────────────────────────

def generate_frames():
    while True:
        if globals.frame_global is None:
            time.sleep(0.01)
            continue
        _, buffer = cv2.imencode(".jpg", globals.frame_global)
        frame = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ── Detection data ────────────────────────────────────────────────────────────

@app.route("/data")
@login_required
def data():
    return jsonify({
        "person":      globals.current_person,
        "weapon":      globals.current_weapon,
        "status":      globals.threat_status,
        "confidence":  globals.current_confidence * 100,
        "boxes":       globals.current_boxes,
        "person_name": globals.current_person,
        "weapon_name": globals.current_weapon,
        "node_id":     session.get("node_id",  NODE_ID),
        "location":    session.get("location", LOCATION),
        "faces_db":    globals.known_names_count,
    })


# ── Upload authorized photo ───────────────────────────────────────────────────

@app.route("/upload_authorized", methods=["POST"])
@admin_required
def upload_authorized():
    try:
        # ── 1. Check file exists in request
        if "photo" not in request.files:
            return jsonify({"success": False, "error": "No file received. Make sure field name is 'photo'."}), 400

        file = request.files["photo"]
        name = request.form.get("name", "").strip()

        # ── 2. Validate inputs
        if not name:
            return jsonify({"success": False, "error": "Person name is required."}), 400
        if not file or not file.filename:
            return jsonify({"success": False, "error": "No file selected."}), 400

        # ── 3. Check extension
        orig_name = file.filename
        ext = orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else ""
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"success": False,
                            "error": f"Unsupported file type '.{ext}'. Use JPG or PNG."}), 400

        # ── 4. Build a safe filename (keep letters, numbers, spaces, hyphens, underscores)
        safe_name = "".join(
            c if (c.isalnum() or c in " _-") else "_" for c in name
        ).strip().replace(" ", "_")

        if not safe_name:
            return jsonify({"success": False,
                            "error": "Person name contains no valid characters."}), 400

        filename  = f"{safe_name}.{ext}"
        save_path = os.path.join(AUTHORIZED_FOLDER, filename)

        print(f"[Upload] name='{name}'  file='{orig_name}'  saving to: {save_path}")

        # ── 5. Save the file
        file.save(save_path)

        # ── 6. Confirm it was saved
        if not os.path.exists(save_path):
            return jsonify({"success": False,
                            "error": f"File was not created at {save_path}. Check folder permissions."}), 500

        saved_size = os.path.getsize(save_path)
        print(f"[Upload] Saved OK ({saved_size} bytes)")

        # ── 7. Reload face encodings using the detector module directly
        #       detector.AUTHORIZED_FOLDER is absolute — same path as ours.
        names = detector.reload_encodings()
        print(f"[Upload] Reload done. Faces: {names}")

        return jsonify({
            "success":   True,
            "saved_as":  filename,
            "save_path": save_path,
            "size_bytes": saved_size,
            "total":     len(names),
            "names":     names,
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Delete authorized photo ───────────────────────────────────────────────────

@app.route("/admin/delete_authorized", methods=["POST"])
@admin_required
def delete_authorized():
    data = request.get_json(silent=True) or {}
    filename = os.path.basename(data.get("filename", ""))
    if not filename:
        return jsonify({"success": False, "error": "No filename provided"}), 400
    path = os.path.join(AUTHORIZED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        detector.reload_encodings()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": f"File not found: {filename}"}), 404


# ── List authorized persons ───────────────────────────────────────────────────

@app.route("/admin/authorized_list")
@admin_required
def authorized_list():
    files = [
        f for f in os.listdir(AUTHORIZED_FOLDER)
        if os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")
    ]
    persons = [
        {"filename": f, "name": os.path.splitext(f)[0].replace("_", " ")}
        for f in sorted(files)
    ]
    return jsonify({"persons": persons, "folder": AUTHORIZED_FOLDER})


# ── User management ───────────────────────────────────────────────────────────

@app.route("/admin/users")
@admin_required
def admin_users():
    return jsonify({"users": get_all_users()})


@app.route("/admin/create_user", methods=["POST"])
@admin_required
def admin_create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "user")
    node_id  = data.get("node_id", "NODE-B1").strip()
    location = data.get("location", "Zone B").strip()
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    try:
        create_user(username, password, role, node_id, location)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/delete_user", methods=["POST"])
@admin_required
def admin_delete_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    try:
        delete_user(username)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Debug endpoint (check folder path) ───────────────────────────────────────

@app.route("/admin/debug_folder")
@admin_required
def debug_folder():
    """Returns the exact folder path being used — helpful for diagnosing upload issues."""
    contents = []
    if os.path.isdir(AUTHORIZED_FOLDER):
        contents = os.listdir(AUTHORIZED_FOLDER)
    return jsonify({
        "authorized_folder": AUTHORIZED_FOLDER,
        "exists": os.path.isdir(AUTHORIZED_FOLDER),
        "contents": contents,
        "detector_folder": detector.AUTHORIZED_FOLDER,
        "folders_match": AUTHORIZED_FOLDER == detector.AUTHORIZED_FOLDER,
    })


# ── Server startup ────────────────────────────────────────────────────────────

def run_flask():
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)


def run_ws():
    asyncio.run(start_websocket())


if __name__ == "__main__":
    threading.Thread(target=run_ws, daemon=True).start()
    threading.Thread(target=process_loop, daemon=True).start()
    run_flask()