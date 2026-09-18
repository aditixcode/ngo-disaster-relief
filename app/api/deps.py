"""
API Dependencies and Authentication/Authorization Guards.

Provides:
- `get_db`: Database session injection.
- `oauth2_scheme`: OAuth2 Bearer token extraction for Swagger UI integration.
- `get_current_user`: Decodes JWT token and validates user in the database.
- `require_roles`: Reusable role-based access control (RBAC) dependency factory.
"""

from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# OAuth2 scheme configures Swagger UI to show the 'Authorize' button
# and look for the token at /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates the Bearer JWT token from the Authorization header,
    decodes the user identity ('sub'), and retrieves the User record from the database.
    Raises HTTP 401 Unauthorized if the token is invalid, expired, or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def require_roles(allowed_roles: List[UserRole]):
    """
    Role-based access control (RBAC) dependency factory.

    Usage in endpoints:
        @router.get("/admin-only", dependencies=[Depends(require_roles([UserRole.ADMIN]))])
        def admin_route(): ...
    """
    def role_verifier(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return current_user

    return role_verifier
