import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("firebasekey.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://edge-ai-based-threat-detection-default-rtdb.firebaseio.com/'
})