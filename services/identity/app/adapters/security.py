"""Adaptadores de seguridad de identity: hash de contraseñas (bcrypt) y tokens (JWT).

Implementan ports.PasswordHasher y ports.TokenIssuer.
Es el único sitio del servicio donde se usan bcrypt y pyjwt.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..domain.model import InvalidToken, UserType
from ..ports.ports import PasswordHasher, TokenIssuer


class BcryptPasswordHasher(PasswordHasher):
    def hash_password(self, password: str) -> str:
        """Hashea una contraseña con un salt aleatorio."""
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Comprueba si la contraseña coincide con su hash."""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class JwtTokenIssuer(TokenIssuer):
    def __init__(self, secret_key: str, expires_minutes: int = 60, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.expires_minutes = expires_minutes
        self.algorithm = algorithm

    def issue_token(self, user_id: str, role: UserType) -> str:
        """Emite un JWT firmado con el id del usuario, su rol y la fecha de caducidad."""
        payload = {
            "user_id": user_id,
            "role": role.value,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self.expires_minutes),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def validate_token(self, token: str) -> dict:
        """Valida firma y caducidad. Devuelve {user_id, role} o lanza InvalidToken."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise InvalidToken("Token has expired.") from None
        except jwt.InvalidTokenError:
            raise InvalidToken("Invalid token.") from None
        return {"user_id": payload["user_id"], "role": payload["role"]}
