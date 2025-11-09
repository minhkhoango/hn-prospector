"""
User filtering and contact info extraction logic.

Refactored from the user-provided quick_filter.py.
"""

import requests
from typing import Optional
import logging
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import re
import warnings

from .models import ContactInfo, UserStatus
from . import hn_client


warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

INTERESTING_PATTERNS = re.compile(
    r"""
    (
        https?://                 # URLs
        |
        [\w\.-]+@[\w\.-]+\.\w+     # Emails
        |
        keybase\.io
        |
        \.dev\b
        |
        \.io\b
        |
        \.com\b
        |
        public\skey
        |
        PGP
    )
    """,
    re.IGNORECASE | re.VERBOSE
)

def process_user(uid: str, session: requests.Session, token_exist: bool) -> Optional[ContactInfo]:
    """
    Processes a single user ID to see if they are "interesting."
    Args:
        uid: The Hacker News user ID.
        session: The requests.Session to use for API calls.

    Returns:
        A ContactInfo object if the user is interesting, else None.
    """

    user_data = hn_client.get_hn_user_info(uid, session)
    if not user_data:
        logging.info(f"User {uid}: no data returned from HN API")
        return None
    
    about_html: str = user_data.get("about", "")
    clean_about: Optional[str] = None
    status: Optional[UserStatus] = None

    # Parse HTML for clean text if present
    github_repo: Optional[str] = None
    if about_html:
        soup = BeautifulSoup(about_html, 'html.parser')
        about_text = soup.get_text(strip=True)
        logging.debug(f"User {uid}: about text extracted (len={len(about_text)})")

        # Check if the 'about' text contains anything interesting
        if INTERESTING_PATTERNS.search(about_text):
            clean_about = about_text
            status = "YES"
            logging.info(f"User {uid}: about section is interesting")
        else:
            logging.info(f"User {uid}: about section not interesting")

    else:
        logging.debug(f"User {uid}: no about section")

    # Always check GitHub profile as a secondary signal. 
    exists = hn_client.check_github_profile(uid, session, token_exist)

    if exists:
        github_repo = f"{hn_client.GITHUB_URL}/{uid}"
        if not status:
            status = "GITHUB_ONLY"
            logging.info(f"User {uid}: github profile found, marking as GITHUB_ONLY")
        else:
            logging.info(f"User {uid}: both about and github present; preferring about status={status}")
    
    if not exists and not status:
        logging.info(f"User {uid}: both about and github not found; skipping user")

    # If we found any interesting signal, return contact card
    if status:
        return ContactInfo(
            uid=uid,
            status=status,
            about=clean_about,
            github_repo=github_repo,
        )

    return None
