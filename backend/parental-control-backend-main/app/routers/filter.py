import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, text

from app.database import get_db
from app.models.db_models import User, FilterPolicyTable
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/filters", tags=["Web Content Filtering"])


class ContentCategoryRequest(BaseModel):
    category_name: str
    is_blocked: bool


class BlacklistUrlRequest(BaseModel):
    url: str


# ==========================================
# 1. TOGGLE CONTENT CATEGORY RESTRICTION
# ==========================================
@router.post("/{child_id}/category", status_code=status.HTTP_200_OK)
async def toggle_content_category(
    child_id: str, 
    payload: ContentCategoryRequest, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Toggles restriction status for web categories in apt.apt_filter_policy_b."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        query = select(FilterPolicyTable).where(
            FilterPolicyTable.child_id == cid,
            FilterPolicyTable.category_key == payload.category_name
        )
        result = await db.execute(query)
        policy = result.scalar_one_or_none()
        
        is_blocked = payload.is_blocked

        if policy:
            policy.is_enabled = is_blocked
        else:
            policy = FilterPolicyTable(
                child_id=cid,
                category_key=payload.category_name,
                is_enabled=is_blocked
            )
            db.add(policy)
            
        await db.commit()
        
        state_msg = "RESTRICTED and blocked" if is_blocked else "ALLOWED and accessible"
        return {
            "status": "success",
            "message": f"Web category '{payload.category_name}' is now {state_msg}.",
            "updated_policy": {
                "child_id": str(child_id),
                "category_key": payload.category_name,
                "is_enabled": is_blocked
            }
        }
    except HTTPException:
        raise
    except Exception as err:
        await db.rollback()
        logger.error(f"Filter Policy Error: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during content category update."
        )


# ==========================================
# 2. APPEND BLACKLIST URL
# ==========================================
@router.post("/{child_id}/blacklist", status_code=status.HTTP_201_CREATED)
async def append_blacklist_url(
    child_id: str, 
    payload: BlacklistUrlRequest, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Appends an explicit target domain block rule safely avoiding missing column errors."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    target_url = payload.url.strip()
    
    try:
        # 1. Primary storage in apt.apt_filter_policy_b
        url_key = f"URL:{target_url}"
        query = select(FilterPolicyTable).where(
            FilterPolicyTable.child_id == cid,
            FilterPolicyTable.category_key == url_key
        )
        res = await db.execute(query)
        policy = res.scalar_one_or_none()
        if policy:
            policy.is_enabled = True
        else:
            policy = FilterPolicyTable(child_id=cid, category_key=url_key, is_enabled=True)
            db.add(policy)

        # 2. Optional sync into apt.apt_blacklisted_urls_b without relying on 'added_date'
        try:
            insert_raw = text("""
                INSERT INTO apt.apt_blacklisted_urls_b (child_id, url)
                VALUES (:cid, :url)
                ON CONFLICT DO NOTHING;
            """)
            await db.execute(insert_raw, {"cid": cid, "url": target_url})
        except Exception as e:
            logger.info(f"Notice syncing to secondary blacklist table: {e}")

        await db.commit()
        
        return {
            "status": "success",
            "message": "Custom URL restriction successfully applied.",
            "blacklisted_url": target_url,
            "child_id": str(child_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Blacklist URL DB insert error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during URL blacklisting."
        )


# ==========================================
# 3. DELETE BLACKLIST URL
# ==========================================
@router.delete("/{child_id}/blacklist/{url_encoded}")
@router.delete("/{child_id}/blacklist")
async def delete_blacklist_url(
    child_id: str, 
    url: str = None, 
    url_encoded: str = None, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Deletes a blacklisted URL entry from active filter rules."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    target_url = (url or url_encoded or "").strip()
    
    try:
        url_key = f"URL:{target_url}"
        
        # 1. Delete from apt.apt_filter_policy_b
        stmt = delete(FilterPolicyTable).where(
            FilterPolicyTable.child_id == cid,
            FilterPolicyTable.category_key == url_key
        )
        await db.execute(stmt)

        # 2. Delete from apt.apt_blacklisted_urls_b if table exists
        try:
            del_raw = text("DELETE FROM apt.apt_blacklisted_urls_b WHERE child_id = :cid AND url = :url;")
            await db.execute(del_raw, {"cid": cid, "url": target_url})
        except Exception as e:
            logger.info(f"Notice deleting from secondary blacklist table: {e}")

        await db.commit()

        return {"status": "success", "message": f"URL {target_url} unblocked."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Blacklist URL DB delete error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during URL unblocking."
        )


# ==========================================
# 4. GET ACTIVE FILTER RULES
# ==========================================
@router.get("/{child_id}/rules")
async def get_child_filter_rules(
    child_id: str, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Returns active web content firewall policies and custom blacklisted URLs."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        query = select(FilterPolicyTable).where(FilterPolicyTable.child_id == cid)
        result = await db.execute(query)
        policies = result.scalars().all()
        
        blocked_categories = [p.category_key for p in policies if p.is_enabled and not p.category_key.startswith("URL:")]
        blacklisted_urls = [p.category_key.replace("URL:", "") for p in policies if p.is_enabled and p.category_key.startswith("URL:")]

        # Query explicit URLs safely without requesting non-existent columns (e.g., added_date)
        try:
            b_query = text("SELECT url FROM apt.apt_blacklisted_urls_b WHERE child_id = :cid;")
            b_res = await db.execute(b_query, {"cid": cid})
            for row in b_res.fetchall():
                if row[0] and row[0] not in blacklisted_urls:
                    blacklisted_urls.append(row[0])
        except Exception as e:
            await db.rollback()
            logger.info(f"Notice fetching secondary blacklist URLs: {e}")
        
        return {
            "child_id": str(child_id),
            "blocked_categories": blocked_categories,
            "blacklisted_urls": blacklisted_urls,
            "custom_blacklisted_urls": blacklisted_urls,
            "safesearch_forced": True
        }
    except HTTPException:
        raise
    except Exception as err:
        await db.rollback()
        logger.error(f"Filter Policy Fetch Error: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed while fetching filter policies."
        )