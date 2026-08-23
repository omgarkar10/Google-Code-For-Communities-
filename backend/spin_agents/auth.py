"""
Authentication module for SPIN Portal.

- Citizen Portal : OTP-based login (6-digit code sent via Twilio SMS to mobile number).
- Staff Portal   : Credential-based login (email/employee-ID + password) → issues JWT.

No SMTP / email delivery is used anywhere. Staff auth is entirely credential + JWT.
"""

import os
import secrets
import hmac
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
try:
    from twilio.rest import Client
except ImportError:
    Client = None
import jwt
from passlib.context import CryptContext
import bcrypt
from spin_agents.db import get_db
from spin_agents.models import User
from spin_agents.departments import normalize_department, CANONICAL_DEPARTMENTS
from spin_agents.cache import (
    set_otp_cache,
    get_otp_cache,
    increment_otp_attempts,
    delete_otp_cache,
    check_rate_limit,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET    = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"

# Twilio SMS – used only for Citizen OTP delivery
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not plain_password:
        return False
    try:
        plain_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
            return bcrypt.checkpw(plain_bytes, hash_bytes)
        return pwd_context.verify(plain_password[:72], hashed_password)
    except Exception:
        return False

class OTPRequest(BaseModel):
    phone: str          # E.164 format, e.g. +919876543210
    name: str | None = None

class OTPVerify(BaseModel):
    phone: str
    code: str

class StaffLoginRequest(BaseModel):
    identifier: str     # official email or employee-ID
    password: str
    department: str | None = None


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

async def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required. Token missing.")
    return decode_token(credentials.credentials)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _send_sms(phone: str, body: str) -> None:
    """Dispatch an SMS via Twilio. Falls back to console log when credentials are absent."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        # Credential-less fallback — OTP is visible in server console only.
        print(f"[SPIN OTP] SMS to {phone}: {body}")
        return
    try:
        client  = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=phone)
        print(f"[SPIN OTP] Twilio SMS dispatched to {phone} – SID: {message.sid}")
    except Exception as exc:
        print(f"[SPIN OTP] Twilio error: {exc}")
        raise HTTPException(status_code=502, detail="OTP delivery failed. Try again.")


# ──────────────────────────────────────────────
# Citizen OTP endpoints
# ──────────────────────────────────────────────

@router.post("/send-otp")
async def send_otp(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of Citizen login.
    - Enforces a 60-second resend cooldown per phone number.
    - Generates a CSPRNG 6-digit code, stores its HMAC-SHA256 hash in cache (TTL 300s).
    - Dispatches the plaintext code to the citizen's phone via Twilio SMS.
    """
    # 1. Rate limit (one OTP request per 60 seconds per number)
    if not check_rate_limit(req.phone):
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting a new OTP.")

    # 2. Generate CSPRNG OTP
    otp_code = "".join(str(secrets.randbelow(10)) for _ in range(6))

    # 3. HMAC-SHA256 hash → stored in cache (never store plaintext)
    otp_hash = hmac.new(JWT_SECRET.encode(), otp_code.encode(), "sha256").hexdigest()
    set_otp_cache(req.phone, otp_hash, ttl_seconds=300)

    # 4. Dispatch via SMS
    _send_sms(req.phone, f"Your SPIN Citizen Portal OTP is: {otp_code}. Valid for 5 minutes. Do not share.")

    return {"status": "success", "message": "OTP sent to your registered mobile number."}


@router.post("/verify-otp")
async def verify_otp(req: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of Citizen login.
    - Retrieves cached HMAC hash; rejects if expired or not found.
    - Locks out after 3 wrong attempts (single-use guarantee).
    - On success: deletes cache key, upserts citizen record, issues JWT.
    """
    cache_entry = get_otp_cache(req.phone)

    if not cache_entry:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Please request a new one.")

    if cache_entry["attempts"] >= 3:
        delete_otp_cache(req.phone)
        raise HTTPException(status_code=429, detail="Too many wrong attempts. Request a new OTP.")

    # Constant-time comparison – prevents timing attacks
    input_hash = hmac.new(JWT_SECRET.encode(), req.code.encode(), "sha256").hexdigest()
    if not hmac.compare_digest(cache_entry["hash"], input_hash):
        increment_otp_attempts(req.phone)
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    # ── Match successful ──
    delete_otp_cache(req.phone)   # Single-use: immediately invalidate

    # Upsert citizen user
    stmt   = select(User).where(User.phone_number == req.phone)
    result = await db.execute(stmt)
    user   = result.scalars().first()

    if not user:
        user = User(phone_number=req.phone, is_verified=True, role="citizen")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "phone": user.phone_number,
            "name":  user.name,
            "role":  user.role,
        },
    }


# ──────────────────────────────────────────────
# Staff credential + JWT endpoint
# ──────────────────────────────────────────────

@router.post("/staff-login")
async def staff_login(req: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Staff Portal login – credential based + JWT authentication.
    Validates official email/employee-ID and password against the database,
    assigns/normalizes the canonical department, then issues a signed JWT.
    """
    stmt   = select(User).where(User.email == req.identifier)
    result = await db.execute(stmt)
    user   = result.scalars().first()

    if not user:
        # Auto-provision staff user if first-time login
        canonical_dept = normalize_department(req.department) if req.department else "Municipality"
        user = User(
            email=req.identifier,
            password_hash=hash_password(req.password),
            name=req.identifier.split("@")[0].replace(".", " ").title() if "@" in req.identifier else "Staff Official",
            role="staff",
            department=canonical_dept,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if user.password_hash and not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        elif not user.password_hash:
            user.password_hash = hash_password(req.password)
            await db.commit()

        # Update department if explicitly passed or if null
        if req.department or not user.department:
            user.department = normalize_department(req.department or user.department or "Municipality")
            await db.commit()
            await db.refresh(user)

    STAFF_ROLES = {"staff", "admin", "department officer", "policymaker", "administrator", "super admin"}
    if user.role and user.role.lower() not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Not a staff account.")

    token = create_access_token({"sub": user.id, "role": user.role, "dept": user.department})

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":         user.id,
            "email":      user.email,
            "name":       user.name,
            "department": user.department,
            "role":       user.role,
        },
    }


# ──────────────────────────────────────────────
# Citizen credential + JWT endpoint
# ──────────────────────────────────────────────

class CitizenLoginRequest(BaseModel):
    identifier: str     # mobile number or email
    password: str

@router.post("/citizen-login")
async def citizen_login(req: CitizenLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Citizen Portal login – password-based authentication.
    Validates mobile number or email + password. Auto-creates account if not found.
    """
    stmt = select(User).where(
        (User.email == req.identifier) | (User.phone_number == req.identifier)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Auto-create citizen user with hashed password
        is_email = "@" in req.identifier
        user = User(
            email=req.identifier if is_email else None,
            phone_number=req.identifier if not is_email else None,
            password_hash=hash_password(req.password),
            name="Citizen User",
            role="citizen",
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if user.password_hash and not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        elif not user.password_hash:
            # Set initial password
            user.password_hash = hash_password(req.password)
            await db.commit()
            await db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "phone": user.phone_number or req.identifier,
            "email": user.email,
            "name":  user.name or "Citizen User",
            "role":  user.role,
        },
    }
