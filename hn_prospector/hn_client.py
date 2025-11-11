"""
Network client for interacting with Hacker News and GitHub.

Handles all HTTP requests, error handling, and rate limiting.
"""

import requests
from requests.adapters import HTTPAdapter, Retry
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup
import logging
import time


# Very important for scraping
HEADERS = {
    "User-Agent": "HN-Prospector-v1.0 (contact: ngominhkhoa2006@gmail.com)"
}

# Base URLs
HN_API_URL = "https://hacker-news.firebaseio.com/v0"
HN_WEB_URL = "https://news.ycombinator.com"
GITHUB_URL = "https://github.com"
GITHUB_API_URL = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def get_session(github_token: str | None) -> requests.Session:
    """Configures a robust session with retries for network resilience."""
    session = requests.Session()
    session.headers.update(HEADERS)

    # --- Github Token Authentication ---
    if github_token:
        session.headers.update({"Accept": "application/vnd.github.v3+json"})
        logging.info("Found GITHUB_TOKEN. Using authenticated GitHub API requests.")
        session.headers.update({"Authorization": f"token {github_token}"})
    else:
        logging.warning("No GITHUB_TOKEN env found. GitHub API requests will be rate-limited")

    # Configure retries for network failures
    retries = Retry(
        total=3,
        backoff_factor=0.5, # expoenntial backoff
        status_forcelist=[500, 502, 503, 504], # only retry on specific server error status code
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

def get_thread_html(thread_id: str, session: requests.Session) -> Optional[str]:
    """Fetches the full HTML content of an HN thread."""
    try:
        url = f"{HN_WEB_URL}/item?id={thread_id}"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching thread HTML for {thread_id}: {e}")
        return None

def get_thread_title(html_content: str) -> str:
    """Extracts the thread title from the HTML content for confirmation."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Get the <title> tag
        title_element = soup.find('title')
        if title_element:
            return title_element.get_text(strip=True) # type: ignore
        
        return "Unknown Title"
    except Exception as e:
        logging.error(f"Error parsing title: {e}")
        return "Unknown Title"  

def get_hn_user_info(uid: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Fetches a user's profile from the HN API."""
    try:
        url = f"{HN_API_URL}/user/{uid}.json"
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching HN user {uid}: {e}")
        return None

def get_github_profile_stats_api(uid: str, session: requests.Session) -> Tuple[bool, int]:
    """
    Checks if a GitHub profile exists and gets its total *public* repository count
    using the GraphQL v4 API. This is a robust proxy for a "non-ghost" account
    and avoids strict v3 search rate limits.

    Returns:
        A tuple of (exists: bool, public_repo_count: int)
    """
    # Gets existence and public repo count, only personal account owned.
    query = f"""
    query {{
      user(login: "{uid}") {{
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC) {{
          totalCount
        }}
      }}
    }}
    """
    payload = {"query": query}

    try:
        response = session.post(GITHUB_GRAPHQL_URL, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            # Handle errors, e.g., user not found
            if data['errors'][0].get("type") == "NOT_FOUND":
                logging.info(f"GitHub user {uid} not found via API.")
            else:
                logging.warning(f"GraphQL error for user {uid}: {data['errors']}")
            return False, 0
        
        user_data = data.get("data", {}).get("user")
        
        if user_data is None:
            # This can happen if the user exists but is not a 'User' type (e.g., 'Organization')
            # or other edge cases.
            logging.info(f"GitHub user {uid} not found or is not a User.")
            return False, 0
        
        repo_count = user_data.get("repositories", {}).get("totalCount", 0)
        return True, repo_count

    except requests.RequestException as e:
        logging.warning(f"Error checking GitHub GraphQL API for {uid}: {e}")
        return False, 0
    except Exception as e:
        logging.error(f"Unexpected error parsing GraphQL response for {uid}: {e}")
        return False, 0
    
def check_github_profile_scrape(uid: str, session: requests.Session) -> bool:
    """Checks if a GitHub profile exists for a given username."""
    try:
        url = f"{GITHUB_URL}/{uid}"
        response = session.head(url, timeout=3, allow_redirects=True)
        # Be nice to github
        time.sleep(2)
        logging.info(f"Checked github profile for {uid} -> {url}, response code is {response.status_code}")
        return response.status_code == 200
    except requests.RequestException as e:
        logging.warning(f"Error checking GitHub API for {uid}: {e}")
        return False
