"""
Parses HN thread HTML to extract comments grouped by user.

Refactored from the user-provided parser.py.
"""

from collections import defaultdict
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Tuple
import logging


def _get_comment_text(comment_div: Tag) -> str:
    """
    Extracts the clean text from a 'commtext' div, handling
    <p> tags and other elements correctly.
    """
    comment_parts: List[str] = []
    try:
        for element in comment_div.children:
            if isinstance(element, Tag) and element.name == 'p':
                if comment_parts:
                    comment_parts.append('\n\n') # Add paragraph break
                comment_parts.append(str(element.get_text(strip=True)))
            elif not isinstance(element, Tag):
                # Capture main comment text that isn't in a <p>
                text = str(element).strip()
                if text:
                    comment_parts.append(text)
                
        return "".join(comment_parts).strip()
    except Exception as e:
        logging.warning(f"Error parsing a comment div: {e}")
        return ""

def parse_comments_by_user(html_content: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parses an HTML string from a Hacker News thread and extracts all comments,
    grouped by user. Each comment is stored as a tuple containing the
    parent comment's text and the user's comment text.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    comments_by_user: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    comment_trs = soup.find_all('tr', class_='comtr')

    for i, comment_tr in enumerate(comment_trs):
        user_tag = comment_tr.find('a', class_='hnuser')
        comment_div = comment_tr.find('div', class_='commtext')

        if user_tag and comment_div:
            username: str = str(user_tag.get_text(strip=True))
            user_comment_text: str = _get_comment_text(comment_div)

            if not user_comment_text:
                continue 
            
            preceding_comment_text = ""
            
            # Get the current comment's indentation level
            ind_tag = comment_tr.find('td', class_='ind')
            if ind_tag and ind_tag.has_attr('indent'):
                current_indent = int(str(ind_tag['indent']))
                
                # Look backwards for the parent comment (previous comment with lower indent)
                if current_indent > 0:
                    for j in range(i - 1, -1, -1):
                        prev_tr = comment_trs[j]
                        prev_ind_tag = prev_tr.find('td', class_='ind')
                        
                        if prev_ind_tag and prev_ind_tag.has_attr('indent'):
                            prev_indent = int(str(prev_ind_tag['indent']))
                            
                            # Found the parent comment (indent is exactly 1 less)
                            if prev_indent == current_indent - 1:
                                parent_comment_div = prev_tr.find('div', class_='commtext')
                                if parent_comment_div:
                                    preceding_comment_text = _get_comment_text(parent_comment_div)
                                break
            
            comments_by_user[username].append(
                (preceding_comment_text, user_comment_text)
            )
    
    return dict(comments_by_user)
