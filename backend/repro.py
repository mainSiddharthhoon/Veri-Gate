import asyncio
from app.core.database import get_db
from app.database.repositories import get_face_verification_by_session, get_document_by_session

def run():
    db = get_db()
    session_id = "00000000-0000-0000-0000-000000000000"
    print("Fetching face verification...")
    try:
        res = get_face_verification_by_session(db, session_id)
        print("Face result:", res)
    except Exception as e:
        print("Face Error:", repr(e))

    print("Fetching document...")
    try:
        res = get_document_by_session(db, session_id)
        print("Doc result:", res)
    except Exception as e:
        print("Doc Error:", repr(e))

run()
