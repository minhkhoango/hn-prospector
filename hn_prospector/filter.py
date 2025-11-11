"""
User filtering and contact info extraction logic.
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

def process_user(
    uid: str, 
    session: requests.Session, 
    token_exist: bool,
    min_repo_count: int
) -> Optional[ContactInfo]:
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
        logging.info(f"{uid}: no data returned from HN API")
        return None
    
    about_html: str = user_data.get("about", "")
    clean_about: Optional[str] = None
    status: Optional[UserStatus] = None

    # Parse HTML for clean text if present
    github_repo: Optional[str] = None
    if about_html:
        soup = BeautifulSoup(about_html, 'html.parser')
        about_text = soup.get_text(strip=True)
        logging.debug(f"{uid}: about text extracted (len={len(about_text)})")

        # Check if the 'about' text contains anything interesting
        if INTERESTING_PATTERNS.search(about_text):
            clean_about = about_text
            status = "YES"
            logging.info(f"{uid}: about section is interesting")
        else:
            logging.info(f"{uid}: about section not interesting")

    else:
        logging.debug(f"{uid}: no about section")

    # --- GitHub Profile Check ---
    github_repo: Optional[str] = None
    github_profile_is_valid: bool = False

    if token_exist:
        # Use the efficient GraphQL API
        try:
            exists, repo_count = hn_client.get_github_profile_stats_api(uid, session)

            if exists and repo_count >= min_repo_count:
                github_profile_is_valid = True
                logging.info(f"User {uid}: GitHub profile is valid with {repo_count} public repos.")
            elif exists:
                logging.info(f"User {uid}: GitHub profile found but only {repo_count} public repos. Skipping profile.")
            else:
                pass
        except requests.RequestException as e:
            logging.warning(f"Error checking GitHub API for {uid}: {e}")
            github_profile_is_valid = False
    else:
        # Web scraping mode (no token), just check for existence
        logging.info(f"{uid}: No GitHub token. Falling back to web scrape check.")
        github_profile_is_valid = hn_client.check_github_profile_scrape(uid, session)

    # --- Combine and Decide ---
    if github_profile_is_valid:
        github_repo = f"{hn_client.GITHUB_URL}/{uid}"
        if not status:
            status = "GITHUB_ONLY"
            logging.info(f"{uid}: Valid github profile found, marking as GITHUB_ONLY")
        else:
            logging.info(f"{uid}: both about and vaild github present; preferring status={status}")

    if not github_profile_is_valid and not status:
        logging.info(f"User {uid}: No interesting about section and no valid github profile; skipping user")
        return None
    
    # If we found any interesting signal, return contact card
    if status:
        return ContactInfo(
            uid=uid,
            status=status,
            about=clean_about,
            github_repo=github_repo,
        )

    return None
