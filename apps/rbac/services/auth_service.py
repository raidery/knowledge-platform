from datetime import datetime, timedelta, timezone

from apps.rbac.models.user import User
from apps.rbac.schemas.auth import CredentialsSchema, JWTOut, JWTPayload
from apps.rbac.services.user_service import user_service
from apps.rbac.utils.jwt_utils import create_access_token


class AuthService:
    async def authenticate(self, credentials: CredentialsSchema) -> User:
        return await user_service.authenticate(credentials)

    async def create_access_token(self, user: User) -> JWTOut:
        from config.settings import settings

        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + access_token_expires
        return JWTOut(
            access_token=create_access_token(
                data=JWTPayload(
                    user_id=user.id,
                    username=user.username,
                    is_superuser=user.is_superuser,
                    exp=expire,
                )
            ),
            username=user.username,
        )


auth_service = AuthService()
