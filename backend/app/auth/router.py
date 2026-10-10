from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.sql import get_db, User
from backend.app.auth.security import verify_password, create_access_token
from backend.app.auth.deps import get_current_user
from backend.app.audit.service import record_audit_log

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool

class QuickLoginRequest(BaseModel):
    role: str = "investigator"

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/quick-login", response_model=LoginResponse)
def quick_login(req: QuickLoginRequest, db: Session = Depends(get_db)):
    """1-Click role selection login for zero-password friction."""
    target_role = req.role.lower().strip()
    if target_role not in ["admin", "investigator", "viewer"]:
        target_role = "investigator"

    # Find existing user by role or username
    user = db.query(User).filter(User.role == target_role).first()
    if not user:
        from scripts.seed_users import hash_password
        default_uname = "admin" if target_role == "admin" else ("investigator1" if target_role == "investigator" else "viewer1")
        user = User(
            username=default_uname,
            role=target_role,
            password_hash=hash_password("CaseConnect2026!"),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"sub": user.id, "username": user.username, "role": user.role})
    
    record_audit_log(
        db=db,
        user_id=user.id,
        action="quick_login",
        object_type="user",
        object_id=user.id,
        details={"username": user.username, "role": user.role}
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active
        )
    )

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with username and password, with fallback for demo convenience."""
    uname = req.username.strip().lower()
    
    # Check if exact user exists
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user:
        # Check case-insensitive or role-based alias
        if uname in ["admin", "investigator", "investigator1", "viewer", "viewer1"]:
            role = "admin" if "admin" in uname else ("viewer" if "viewer" in uname else "investigator")
            user = db.query(User).filter(User.role == role).first()
            if not user:
                from scripts.seed_users import hash_password
                user = User(
                    username=uname,
                    role=role,
                    password_hash=hash_password("CaseConnect2026!"),
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)

    # Allow if password verifies OR if it matches demo credentials
    valid = False
    if user:
        if verify_password(req.password, user.password_hash):
            valid = True
        elif req.password in ["admin123", "AdminPass1234!", "inves123", "OfficerPass1234!", "ViewerPass1234!", "CaseConnect2026!", "password", "123456"]:
            valid = True
        elif uname in ["admin", "investigator", "investigator1", "viewer", "viewer1"]:
            # Never block demo accounts
            valid = True

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    token = create_access_token(data={"sub": user.id, "username": user.username, "role": user.role})
    
    # Audit log login
    record_audit_log(
        db=db,
        user_id=user.id,
        action="login",
        object_type="user",
        object_id=user.id,
        details={"username": user.username, "role": user.role}
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active
        )
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get profile of currently logged-in user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active
    )

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Log out user and record in audit log."""
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="logout",
        object_type="user",
        object_id=current_user.id,
        details={"username": current_user.username}
    )
    return {"status": "success", "message": "Logged out successfully"}
