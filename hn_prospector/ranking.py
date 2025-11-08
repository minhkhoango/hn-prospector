"""
Handles the business logic for processing and ranking users.

This keeps the main.py file clean and focused on orchestration.
"""

from typing import List

from .models import ContactInfo, RankedUser


def build_ranked_user(
    user_id: str,
    comments: List[str],
    contact_info: ContactInfo
) -> RankedUser:
    """
    Factory function to create a RankedUser object from its parts.
    
    This encapsulates the logic for calculating metrics.
    """
    comment_count = len(comments)
    word_count = sum(len(c.split()) for c in comments)
    
    return RankedUser(
        user_id=user_id,
        contact=contact_info,
        comments=comments,
        comment_count=comment_count,
        total_word_count=word_count
    )


def sort_users(users: List[RankedUser]) -> List[RankedUser]:
    """
    Sorts a list of RankedUser objects based on the project's
    ranking criteria.
    """
    
    return sorted(
        users,
        key=lambda u: (u.comment_count, u.total_word_count),
        reverse=True
    )