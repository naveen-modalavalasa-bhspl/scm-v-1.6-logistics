from datetime import datetime, timezone
import secrets
import string
import hashlib
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, ApiKey, UserRole
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyReveal
from app.utils.dependencies import get_current_user

router = APIRouter()

def generate_api_key() -> str:
    """Generate a random 32-character API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(32))

def hash_api_key(key: str) -> str:
    """Hash the API key using SHA-256"""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

@router.post("", response_model=ApiKeyReveal)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API Key for the current user.
    The raw key is returned ONLY once in the response.
    """
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    linked_user_ids = list(payload.linked_user_ids or [])
    if payload.linked_role_ids:
        result = await db.execute(
            select(UserRole.user_id).where(UserRole.role_id.in_(payload.linked_role_ids))
        )
        role_user_ids = {row[0] for row in result.all()}
        linked_user_ids = list(set(linked_user_ids) | role_user_ids)

    # Auto-generate URL endpoints based on scopes
    scopes_list = payload.scopes or []
    paths = []
    for scope in scopes_list:
        if scope == "masters:items:read" or scope.startswith("masters:items:"):
            paths.append("/api/v1/external/masters/items")
        elif scope == "masters:vendors:read":
            paths.append("/api/v1/external/masters/vendors")
        elif scope == "inventory:stock-balance:read" or scope.startswith("inventory:stock-balance:"):
            paths.append("/api/v1/external/inventory/stock")
        elif scope == "indent:acknowledgement:read":
            paths.append("/api/v1/external/indent/acknowledgements")
            
    # Dedup and preserve order
    seen = set()
    deduped_paths = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            deduped_paths.append(p)
            
    base_url = str(request.base_url).rstrip("/")
    generated_endpoint = ", ".join(f"{base_url}{p}" for p in deduped_paths) if deduped_paths else None

    new_key = ApiKey(
        user_id=current_user.id,
        name=payload.name,
        key_hash=key_hash,
        scopes=json.dumps(payload.scopes) if payload.scopes else "[]",
        linked_user_ids=linked_user_ids,
        endpoint=generated_endpoint,
        expires_at=payload.expires_at,
        is_active=True,
    )

    db.add(new_key)

    await db.commit()
    await db.refresh(new_key)
    
    # Parse scopes back to list for response
    parsed_scopes = json.loads(new_key.scopes) if new_key.scopes else []

    return ApiKeyReveal(
        id=new_key.id,
        name=new_key.name,
        scopes=parsed_scopes,
        linked_user_ids=new_key.linked_user_ids or [],
        endpoint=new_key.endpoint,
        expires_at=new_key.expires_at,
        is_active=new_key.is_active,
        last_used_at=new_key.last_used_at,
        created_at=new_key.created_at,
        raw_key=raw_key,
    )

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    
    response_keys = []
    for key in keys:
        parsed_scopes = json.loads(key.scopes) if key.scopes else []
        response_keys.append(
            ApiKeyResponse(
                id=key.id,
                name=key.name,
                scopes=parsed_scopes,
                linked_user_ids=key.linked_user_ids or [],
                endpoint=key.endpoint,
                expires_at=key.expires_at,
                is_active=key.is_active,
                last_used_at=key.last_used_at,
                created_at=key.created_at,
            )
        )
        
    return response_keys

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (delete) an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")

    await db.delete(key)
    await db.commit()
    return {"success": True, "message": "API Key revoked successfully"}
