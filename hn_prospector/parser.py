"""
Parses HN thread HTML to extract comments grouped by user.

Refactored from the user-provided parser.py.
"""

from collections import defaultdict
from bs4 import BeautifulSoup, Tag
from typing import Dict, List

def parse_comments_by_user(html_content: str) -> Dict[str, List[str]]:
    """
    Parses an HTML string from a Hacker News thread and extracts all comments,
    grouped by user.

    Args:
        html_content: A string containing the HTML of the Hacker News thread.

    Returns:
        A dictionary where keys are usernames and values are lists of their
        comment texts.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    comments_by_user: Dict[str, List[str]] = defaultdict(list)

    comment_trs = soup.find_all('tr', class_='comtr')

    for comment_tr in comment_trs:
        user_tag = comment_tr.find('a', class_='hnuser')
        comment_div = comment_tr.find('div', class_='commtext')

        if user_tag and comment_div:
            username: str = str(user_tag.get_text(strip=True))
            
            comment_parts: List[str] = []
            for element in comment_div.children:
                if isinstance(element, Tag) and element.name == 'p':
                    if comment_parts:
                        comment_parts.append('\n\n')
                    comment_parts.append(str(element.get_text(strip=True)))
                elif not isinstance(element, Tag):
                    text = str(element).strip()
                    if text:
                        comment_parts.append(text)
                
            comment_text: str = "".join(comment_parts).strip()

            if comment_text:
                comments_by_user[username].append(comment_text)
    
    return dict(comments_by_user)
