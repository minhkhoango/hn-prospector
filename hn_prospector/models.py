"""
Data models for the HN Prospector.

This defines the core data structures used throughout the application,
ensuring type safety and clarity.
"""

from dataclasses import dataclass
from typing import List, Optional, Literal, TypedDict, Tuple

# Status can be "YES" (info in 'about') or "GITHUB_ONLY"
UserStatus = Literal["YES", "GITHUB_ONLY"]


@dataclass(frozen=True)
class ContactInfo:
    """
    Stores the "contact" information for a user.
    """
    uid: str
    status: UserStatus
    about: Optional[str]
    github_repo: Optional[str]


# Detailed Typed Dict for RankedUser to_dict function output
class ContactDict(TypedDict):
    about: Optional[str]
    github_repo: Optional[str]
    status: UserStatus


class MetricsDict(TypedDict):
    comment_count: int
    total_word_count: int


class RankedUserDict(TypedDict):
    uid: str
    contact: ContactDict
    metrics: MetricsDict
    comments: List[Tuple[str, str]]


@dataclass
class RankedUser:
    """
    The final, combined data structure for an output-ready user.
    """
    uid: str
    contact: ContactInfo
    # preceeding comment and user's comment
    comments: List[Tuple[str, str]]
    comment_count: int
    total_word_count: int

    def to_dict(self) -> RankedUserDict:
        """Converts the object to a dictionary for JSON serialization."""
        return {
            "uid": self.uid,
            "contact": {
                "about": self.contact.about,
                "github_repo": self.contact.github_repo,
                "status": self.contact.status,
            },
            "metrics": {
                "comment_count": self.comment_count,
                "total_word_count": self.total_word_count,
            },
            "comments": self.comments,
        }