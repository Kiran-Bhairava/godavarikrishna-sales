from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError
from database import get_db
from dependencies import get_current_user
from security import verify_password, create_access_token, create_refresh_token, decode_token
from models import User, UserSession
from schemas import LoginRequest, RefreshRequest, LogoutRequest
from config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Service logic ─────────────────────────────────────────────────────────────

def _login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    payload = {
        "sub":        str(user.id),
        "role":       user.role.name,
        "role_level": user.role.level,
        "scope_type": str(user.scope_type) if user.scope_type else None,
        "scope_id":   user.scope_id,
    }

    access_token  = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    session = UserSession(
        user_id       = user.id,
        refresh_token = refresh_token,
        expires_at    = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user": {
            "id":         user.id,
            "full_name":  user.full_name,
            "email":      user.email,
            "role":       user.role.name,
            "scope_type": str(user.scope_type) if user.scope_type else None,
            "scope_id":   user.scope_id,
        }
    }


def _refresh(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.revoked_at == None
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Session not found or already revoked")

    new_access_token = create_access_token({
        "sub":        payload["sub"],
        "role":       payload["role"],
        "role_level": payload["role_level"],
        "scope_type": payload["scope_type"],
        "scope_id":   payload["scope_id"],
    })

    return {"access_token": new_access_token}


def _logout(db: Session, refresh_token: str):
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.revoked_at == None
    ).first()

    if session:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    return _login(db, body.email, body.password)


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return _refresh(db, body.refresh_token)


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    _logout(db, body.refresh_token)
    return {"message": "Logged out successfully"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id":         current_user.id,
        "full_name":  current_user.full_name,
        "email":      current_user.email,
        "role":       current_user.role.name,
        "scope_type": str(current_user.scope_type) if current_user.scope_type else None,
        "scope_id":   current_user.scope_id,
    }