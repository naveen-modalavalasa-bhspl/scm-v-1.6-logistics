from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.carrier import CarrierUser
from app.models.master import Vendor
from app.schemas.carrier_auth import (
    CarrierLoginRequest, CarrierTokenResponse, CarrierUserResponse, CarrierChangePassword,
)
from app.services.auth_service import (
    hash_password, verify_password, create_access_token,
)
from app.utils.dependencies import get_current_carrier_user
from app.config import settings

router = APIRouter()

_LOCKOUT_THRESHOLD = 5
_LOCKOUT_MINUTES = 15
_DUMMY_BCRYPT = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8wW3GtsKzgYBWvP9oKzqW1xk9pqH8."


def _build_carrier_user_response(cu: CarrierUser) -> CarrierUserResponse:
    return CarrierUserResponse(
        id=cu.id,
        vendor_id=cu.vendor_id,
        vendor_name=cu.vendor.name if cu.vendor else None,
        vendor_code=cu.vendor.vendor_code if cu.vendor else None,
        username=cu.username,
        email=cu.email,
        full_name=cu.full_name,
        phone=cu.phone,
        is_active=cu.is_active,
        must_change_password=cu.must_change_password,
        last_login=cu.last_login,
        created_at=cu.created_at,
    )


@router.post("/login", response_model=CarrierTokenResponse)
async def carrier_login(
    request: Request,
    payload: CarrierLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    identifier = payload.username.strip()
    ident_lower = identifier.lower()
    import re as _re
    ident_normalized = _re.sub(r'[^a-zA-Z0-9_]', '_', identifier).lower()
    res = await db.execute(
        select(CarrierUser).where(
            (func.lower(CarrierUser.username) == ident_lower)
            | (func.lower(CarrierUser.email) == ident_lower)
            | (func.lower(CarrierUser.username) == ident_normalized)
        )
    )
    cu = res.scalar_one_or_none()

    if cu is None:
        try:
            verify_password(payload.password, _DUMMY_BCRYPT)
        except Exception:
            pass

    # Account lockout check
    if cu is not None and cu.locked_until is not None:
        cutoff = cu.locked_until
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        if cutoff > datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    if not cu or not cu.is_active or not verify_password(payload.password, cu.password_hash):
        # Vendor must also be active
        if cu is not None and cu.vendor is not None and not cu.vendor.is_active:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if cu is not None:
            cu.failed_login_attempts = (cu.failed_login_attempts or 0) + 1
            if cu.failed_login_attempts >= _LOCKOUT_THRESHOLD:
                cu.locked_until = datetime.now(timezone.utc) + timedelta(minutes=_LOCKOUT_MINUTES)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Vendor must be active to allow login
    if cu.vendor is None or not cu.vendor.is_active:
        raise HTTPException(status_code=403, detail="Carrier account is inactive")

    cu.failed_login_attempts = 0
    cu.locked_until = None
    cu.last_login = datetime.now(timezone.utc)
    await db.flush()

    token_data = {
        "sub": str(cu.id),
        "username": cu.username,
        "carrier_portal": True,
        "vendor_id": cu.vendor_id,
    }
    access_token = create_access_token(token_data)
    await db.commit()

    return CarrierTokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_build_carrier_user_response(cu),
    )


@router.get("/me", response_model=CarrierUserResponse)
async def carrier_me(
    current_carrier: CarrierUser = Depends(get_current_carrier_user),
):
    return _build_carrier_user_response(current_carrier)


@router.post("/logout")
async def carrier_logout(
    request: Request,
    current_carrier: CarrierUser = Depends(get_current_carrier_user),
    db: AsyncSession = Depends(get_db),
):
    # Stateless logout — frontend drops the token. But blocklist it here.
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
async def carrier_change_password(
    payload: CarrierChangePassword,
    current_carrier: CarrierUser = Depends(get_current_carrier_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_carrier.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_carrier.password_hash):
        raise HTTPException(status_code=400, detail="New password must differ from the current password")
    current_carrier.password_hash = hash_password(payload.new_password)
    current_carrier.password_changed_at = datetime.now(timezone.utc)
    current_carrier.must_change_password = False
    await db.commit()
    return {"success": True, "message": "Password changed successfully"}
