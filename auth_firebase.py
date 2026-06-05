import hashlib
import firebase_admin
from firebase_admin import credentials, db
import os

# Guard against duplicate initialization
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), "firebasekey.json"))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://edge-ai-based-threat-detection-default-rtdb.firebaseio.com/'
    })

# ── DEFAULT ADMIN (hard-coded fallback) ──────────────────────────────────────
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin",
}

def _hash(password: str) -> str:
    """SHA-256 hash a password string."""
    return hashlib.sha256(password.encode()).hexdigest()

def _ensure_default_admin():
    """Seeds the default admin into Firebase if no users exist yet."""
    ref = db.reference("users")
    users = ref.get()
    if not users or DEFAULT_ADMIN["username"] not in users:
        ref.child(DEFAULT_ADMIN["username"]).set({
            "password": _hash(DEFAULT_ADMIN["password"]),
            "role": "admin",
            "node_id": "NODE-A1",
            "location": "Main Entrance",
        })
        print(f"✅ Default admin seeded: {DEFAULT_ADMIN['username']} / {DEFAULT_ADMIN['password']}")

# Run once at import time
try:
    _ensure_default_admin()
except Exception as e:
    print("Firebase seed warning:", e)


def verify_user(username: str, password: str):
    """
    Returns (True, role, node_id, location) on success,
            (False, None, None, None) on failure.
    Supports both hashed (new) and plain-text (legacy) passwords.
    """
    ref = db.reference("users")
    users = ref.get()

    if not users or username not in users:
        return False, None, None, None

    user = users[username]
    stored_pw = user.get("password", "")

    # Accept hashed match OR legacy plain-text match (so existing accounts still work)
    if stored_pw == _hash(password) or stored_pw == password:
        role     = user.get("role", "user")
        node_id  = user.get("node_id", "NODE-A1")
        location = user.get("location", "Main Entrance")
        return True, role, node_id, location

    return False, None, None, None


def create_user(username: str, password: str, role: str = "user",
                node_id: str = "NODE-B1", location: str = "Zone B"):
    """Creates or overwrites a user in Firebase."""
    db.reference(f"users/{username}").set({
        "password": _hash(password),
        "role": role,
        "node_id": node_id,
        "location": location,
    })


def delete_user(username: str):
    """Deletes a user from Firebase. Cannot delete the default admin."""
    if username == DEFAULT_ADMIN["username"]:
        raise ValueError("Cannot delete the default admin account.")
    db.reference(f"users/{username}").delete()


def get_all_users():
    """Returns a list of user dicts (without passwords) for the admin panel."""
    ref = db.reference("users")
    users = ref.get() or {}
    result = []
    for uname, data in users.items():
        result.append({
            "username": uname,
            "role":     data.get("role", "user"),
            "node_id":  data.get("node_id", "NODE-A1"),
            "location": data.get("location", "Main Entrance"),
        })
    return result