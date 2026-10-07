import logging
import re
from typing import Optional, Tuple
from google_play_scraper import app as play_store_app

logger = logging.getLogger(__name__)

def is_version_older(current_ver: str, latest_ver: str) -> bool:
    if not current_ver or not latest_ver:
        return False
    if "varies" in latest_ver.lower() or "varies" in current_ver.lower():
        return False

    def parse_ver(v: str):
        parts = []
        for p in re.findall(r'\d+', v):
            try:
                parts.append(int(p))
            except ValueError:
                pass
        return parts

    current_parts = parse_ver(current_ver)
    latest_parts = parse_ver(latest_ver)

    for c, l in zip(current_parts, latest_parts):
        if c < l:
            return True
        elif c > l:
            return False

    if len(current_parts) < len(latest_parts):
        return any(x > 0 for x in latest_parts[len(current_parts):])

    return False

def check_app_version(package_name: str, current_version: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if the app is outdated compared to the version on the Google Play Store.
    Returns: (is_outdated, play_store_url)
    """
    play_store_url = f"https://play.google.com/store/apps/details?id={package_name}"
    try:
        info = play_store_app(package_name)
        latest_version = info.get("version")
        if latest_version:
            if is_version_older(current_version, latest_version):
                return True, play_store_url
        return False, None
    except Exception as e:
        logger.warning(f"Failed to lookup package version for {package_name}: {e}")
        return False, None
