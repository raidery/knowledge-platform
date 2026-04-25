import jwt

from apps.rbac.schemas.auth import JWTPayload


def create_access_token(*, data: JWTPayload):
    # Lazy import to avoid circular import
    from config.settings.config import settings

    payload = data.model_dump().copy()
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
