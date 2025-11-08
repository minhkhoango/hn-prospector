"""
User filtering and contact info extraction logic.

Refactored from the user-provided quick_filter.py.
"""

import requests
from typing import Optional
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

def process_user(uid: str, session: requests.Session) -> Optional[ContactInfo]:
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
        return None
    
    about_html: str = user_data.get("about", "")
    clean_about: Optional[str] = None
    status: Optional[UserStatus] = None

    if about_html:
        # Parse HTML for clean taxt
        soup = BeautifulSoup(about_html, 'html.parser')
        about_text = soup.get_text(strip=True)

        # Check if the 'about' text contains anything interesting
        if INTERESTING_PATTERNS.search(about_text):
            clean_about = about_text
            status = "YES"

        # If 'about' wasn't interesting, check for Github
        github_repo: Optional[str] = None
        if not status:
            if hn_client.check_github_profile(uid, session):
                github_repo = f"{hn_client.GITHUB_URL}/{uid}"
                status = "GITHUB_ONLY"
        
        # If we found anything, return contact card
        if status:
            return ContactInfo(
                user_id=uid,
                status=status,
                about=clean_about,
                github_repo=github_repo
            )

        # User is not interesting
        return None
