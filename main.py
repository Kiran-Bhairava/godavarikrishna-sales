from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from auth import router as auth_router
from admin import router as admin_router
from database import get_db
from models import User, Role
from security import hash_password

app = FastAPI(title="GK Sales API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


# ── Bootstrap ─────────────────────────────────────────────────────────────────
# One-time endpoint — creates super_admin role + first super admin user.
# Auto-disabled once any super admin exists.

class BootstrapRequest(BaseModel):
    full_name: str
    email:     EmailStr
    password:  str

@app.post("/bootstrap", tags=["Bootstrap"])
def bootstrap_super_admin(data: BootstrapRequest, db: Session = Depends(get_db)):
    super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()

    if super_admin_role:
        # Role exists — block if super admin user already created
        already_exists = db.query(User).filter(User.role_id == super_admin_role.id).first()
        if already_exists:
            raise HTTPException(400, "Super admin already exists. This endpoint is disabled.")
    else:
        # Very first run — create the role on the fly, no SQL seed needed
        super_admin_role = Role(
            name  = "super_admin",
            label = "Super Admin",
            level = 1,
        )
        db.add(super_admin_role)
        db.flush()  # get role.id before commit

    user = User(
        role_id       = super_admin_role.id,
        full_name     = data.full_name,
        email         = data.email,
        password_hash = hash_password(data.password),
        scope_type    = None,
        scope_id      = None,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Super admin created successfully.",
        "id":      user.id,
        "email":   user.email,
        "role":    super_admin_role.name,
    }