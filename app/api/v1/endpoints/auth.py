"""
Authentication and Authorization Endpoints.

Provides:
- User registration (POST /api/v1/auth/register)
- User login / JWT token issuance (POST /api/v1/auth/login)
- Current user profile (GET /api/v1/auth/me)
- Role-based authorization test endpoints (admin, staff, volunteer, donor)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user account with hashed password and role assignment.",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> User:
    """
    Registers a new user:
    1. Validates input schema.
    2. Ensures email is unique across the system.
    3. Hashes password using bcrypt.
    4. Saves user to database and returns public user profile (excluding password hash).
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_pw,
        role=user_in.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login and JWT token generation",
    description=(
        "Authenticates user credentials and returns a signed JWT access token. "
        "Supports both JSON request bodies ({'email': '...', 'password': '...'}) and "
        "OAuth2 form-data (username and password) used by Swagger's 'Authorize' button."
    ),
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticates a user via email and password.
    Accepts both JSON and OAuth2 form data for maximum client and Swagger compatibility.
    """
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        # Handles application/x-www-form-urlencoded (Swagger UI Authorize button)
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Encode user identity and role into the JWT token payload
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile information of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Protected endpoint: returns the authenticated user's profile.
    Requires Authorization: Bearer <token>
    """
    return current_user


# -----------------------------------------------------------------------------
# Role-Based Access Control (RBAC) Demonstration Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/admin-test",
    summary="Admin only access test",
    description="Accessible exclusively to users with the ADMIN role.",
)
def admin_only_test(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    return {
        "message": "Access granted: You are authorized as an ADMIN.",
        "user": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/staff-test",
    summary="Staff and Admin access test",
    description="Accessible to users with ADMIN or NGO_STAFF roles.",
)
def staff_test(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
):
    return {
        "message": "Access granted: You are authorized as NGO Staff or Admin.",
        "user": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/volunteer-test",
    summary="Volunteer, Staff, and Admin access test",
    description="Accessible to users with ADMIN, NGO_STAFF, or VOLUNTEER roles.",
)
def volunteer_test(
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.VOLUNTEER])
    ),
):
    return {
        "message": "Access granted: You are authorized as a Volunteer, Staff, or Admin.",
        "user": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/donor-test",
    summary="Donor, Staff, and Admin access test",
    description="Accessible to users with ADMIN, NGO_STAFF, or DONOR roles.",
)
def donor_test(
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.DONOR])
    ),
):
    return {
        "message": "Access granted: You are authorized as a Donor, Staff, or Admin.",
        "user": current_user.email,
        "role": current_user.role,
    }
