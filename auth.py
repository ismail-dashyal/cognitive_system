# auth.py
import bcrypt

def hash_password(plain: str) -> str:
    pw = plain.encode("utf8")
    h = bcrypt.hashpw(pw, bcrypt.gensalt())
    return h.decode("utf8")

def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf8"), hashed.encode("utf8"))
    except Exception:
        return False
