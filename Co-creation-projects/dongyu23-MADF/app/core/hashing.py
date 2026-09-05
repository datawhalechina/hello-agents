import bcrypt

class Hasher:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if not plain_password or not hashed_password:
            return False
        try:
            # Direct bcrypt verification
            password_bytes = plain_password.encode('utf-8')
            # Bcrypt has a 72-byte limit. We truncate to match hashing logic.
            if len(password_bytes) > 71:
                password_bytes = password_bytes[:71]
            
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        # Direct bcrypt hashing
        password_bytes = password.encode('utf-8')
        # Bcrypt has a 72-byte limit. We truncate to 71 to be safe.
        if len(password_bytes) > 71:
            password_bytes = password_bytes[:71]
            
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
