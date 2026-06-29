from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.vendor_portal import VendorUser
from app.models.master import Vendor
from app.schemas.vendor_auth import (
    VendorLoginRequest, VendorTokenResponse, VendorUserResponse, VendorChangePassword,
)
from app.services.auth_service import (
    hash_password, verify_password, create_access_token,
)
from app.utils.dependencies import get_current_vendor_user
from app.config import settings

router = APIRouter()

_LOCKOUT_THRESHOLD = 5
_LOCKOUT_MINUTES = 15
_DUMMY_BCRYPT = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8wW3GtsKzgYBWvP9oKzqW1xk9pqH8."


def _build_vendor_user_response(vu: VendorUser) -> VendorUserResponse:
    return VendorUserResponse(
        id=vu.id,
        vendor_id=vu.vendor_id,
        vendor_name=vu.vendor.name if vu.vendor else None,
        vendor_code=vu.vendor.vendor_code if vu.vendor else None,
        username=vu.username,
        email=vu.email,
        full_name=vu.full_name,
        phone=vu.phone,
        is_active=vu.is_active,
        must_change_password=vu.must_change_password,
        last_login=vu.last_login,
        created_at=vu.created_at,
    )


@router.post("/login", response_model=VendorTokenResponse)
async def vendor_login(
    request: Request,
    payload: VendorLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    identifier = payload.username.strip()
    ident_lower = identifier.lower()
    import re as _re
    ident_normalized = _re.sub(r'[^a-zA-Z0-9_]', '_', identifier).lower()
    res = await db.execute(
        select(VendorUser).where(
            (func.lower(VendorUser.username) == ident_lower)
            | (func.lower(VendorUser.email) == ident_lower)
            | (func.lower(VendorUser.username) == ident_normalized)
        )
    )
    vu = res.scalar_one_or_none()

    if vu is None:
        try:
            verify_password(payload.password, _DUMMY_BCRYPT)
        except Exception:
            pass

    # Account lockout check
    if vu is not None and vu.locked_until is not None:
        cutoff = vu.locked_until
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        if cutoff > datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    if not vu or not vu.is_active or not verify_password(payload.password, vu.password_hash):
        if vu is not None and vu.vendor is not None and not vu.vendor.is_active:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if vu is not None:
            vu.failed_login_attempts = (vu.failed_login_attempts or 0) + 1
            if vu.failed_login_attempts >= _LOCKOUT_THRESHOLD:
                vu.locked_until = datetime.now(timezone.utc) + timedelta(minutes=_LOCKOUT_MINUTES)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Vendor must be active to allow login
    if vu.vendor is None or not vu.vendor.is_active:
        raise HTTPException(status_code=403, detail="Supplier account is inactive")

    vu.failed_login_attempts = 0
    vu.locked_until = None
    vu.last_login = datetime.now(timezone.utc)
    await db.flush()

    token_data = {
        "sub": str(vu.id),
        "username": vu.username,
        "vendor_portal": True,
        "vendor_id": vu.vendor_id,
    }
    access_token = create_access_token(token_data)
    await db.commit()

    return VendorTokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_build_vendor_user_response(vu),
    )


@router.get("/me", response_model=VendorUserResponse)
async def vendor_me(
    current_vendor: VendorUser = Depends(get_current_vendor_user),
):
    return _build_vendor_user_response(current_vendor)


@router.post("/logout")
async def vendor_logout(
    request: Request,
    current_vendor: VendorUser = Depends(get_current_vendor_user),
    db: AsyncSession = Depends(get_db),
):
    # Blocklist the token here on logout
    import hashlib
    from app.models.user import TokenBlocklist
    from sqlalchemy.exc import IntegrityError
    auth_header = request.headers.get("authorization", "")
    raw_token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""
    if raw_token:
        from app.services.auth_service import decode_token
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        payload = decode_token(raw_token) or {}
        exp_ts = payload.get("exp")
        exp_dt = None
        if exp_ts:
            try:
                exp_dt = datetime.fromtimestamp(int(exp_ts), tz=timezone.utc).replace(tzinfo=None)
            except Exception:
                exp_dt = None
        try:
            db.add(TokenBlocklist(
                jti=payload.get("jti"),
                token_hash=token_hash,
                user_id=None,
                token_type=payload.get("type", "access"),
                expires_at=exp_dt,
                reason="logout",
            ))
            await db.flush()
        except IntegrityError:
            await db.rollback()
        except Exception:
            await db.rollback()
    return {"success": True, "message": "Logged out"}


@router.post("/change-password")
async def vendor_change_password(
    payload: VendorChangePassword,
    current_vendor: VendorUser = Depends(get_current_vendor_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_vendor.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_vendor.password_hash):
        raise HTTPException(status_code=400, detail="New password must differ from the current password")
    current_vendor.password_hash = hash_password(payload.new_password)
    current_vendor.password_changed_at = datetime.now(timezone.utc)
    current_vendor.must_change_password = False
    await db.commit()
    return {"success": True, "message": "Password changed successfully"}
