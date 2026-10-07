# app/services/child_service.py
import logging
from typing import Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

async def get_child_id(db: AsyncSession, child_identifier: Union[str, int]) -> int:
    """
    Authoritative Enterprise Child Resolution Service:
    Converts incoming child_uuid strings, custom identifiers, or numeric strings
    into the database primary key BIGINT child_id.
    
    1. Queries APT_CHILDREN_B for matching child_id, child_uuid, or linking_code.
    2. Fallbacks to APT_DEVICE_PAIRING_B if unlinked/pairing record.
    3. Raises HTTP 404 Not Found if profile cannot be resolved.
    4. NEVER returns a default child_id (e.g. 1 or 999999).
    """
    if not child_identifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child identifier is required."
        )

    clean_str = str(child_identifier).strip()

    # 1. If numeric integer string, attempt direct child_id query in apt_children_b
    if clean_str.isdigit():
        cid_num = int(clean_str)
        try:
            query = text("SELECT child_id FROM apt_children_b WHERE child_id = :cid LIMIT 1;")
            result = await db.execute(query, {"cid": cid_num})
            row = result.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception as e:
            logger.error(f"Error querying apt_children_b by numeric child_id: {e}")

    # 2. Query apt_children_b by child_uuid or linking_code
    try:
        query = text("""
            SELECT child_id FROM apt_children_b 
            WHERE CAST(child_uuid AS TEXT) = :c_str 
               OR child_uuid::text = :c_str 
               OR linking_code = :c_str 
            LIMIT 1;
        """)
        result = await db.execute(query, {"c_str": clean_str})
        row = result.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception as e:
        logger.error(f"Error querying apt_children_b by uuid/code: {e}")

    # 3. Query apt_device_pairing_b by child_uuid, linking_code, or pairing child_id
    try:
        query_pairing = text("""
            SELECT child_id FROM apt_device_pairing_b 
            WHERE (CAST(child_uuid AS TEXT) = :c_str OR child_uuid::text = :c_str OR linking_code = :c_str) 
              AND child_id IS NOT NULL 
            LIMIT 1;
        """)
        result_p = await db.execute(query_pairing, {"c_str": clean_str})
        row_p = result_p.fetchone()
        if row_p and row_p[0] is not None:
            return int(row_p[0])
    except Exception as e:
        logger.error(f"Error querying apt_device_pairing_b by uuid/code: {e}")

    # 4. If child device cannot be resolved in database, raise HTTP 404 Not Found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Child device profile '{clean_str}' not found."
    )

async def verify_parent_ownership(db: AsyncSession, child_id: int, parent_user_id: int) -> bool:
    """
    Verifies that the resolved BIGINT child_id belongs to the authenticated parent_user_id.
    Raises HTTP 403 Forbidden if the child profile belongs to a different parent.
    Raises HTTP 404 Not Found if the child profile is not found in DB.
    """
    found_child = False

    try:
        query = text("""
            SELECT parent_user_id FROM apt_children_b 
            WHERE child_id = :cid 
            LIMIT 1;
        """)
        result = await db.execute(query, {"cid": child_id})
        row = result.fetchone()
        if row and row[0] is not None:
            found_child = True
            db_parent_id = int(row[0])
            if db_parent_id != parent_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Target child device belongs to another parent account."
                )
            return True

        # Fallback check in apt_device_pairing_b
        query_pairing = text("""
            SELECT parent_id FROM apt_device_pairing_b 
            WHERE child_id = :cid 
            LIMIT 1;
        """)
        result_p = await db.execute(query_pairing, {"cid": child_id})
        row_p = result_p.fetchone()
        if row_p and row_p[0] is not None:
            found_child = True
            db_parent_id = int(row_p[0])
            if db_parent_id != parent_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Target child device belongs to another parent account."
                )
            return True
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Database error during parent ownership verification: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database verification error during ownership validation."
        )

    if not found_child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child device profile not found."
        )

    return True

