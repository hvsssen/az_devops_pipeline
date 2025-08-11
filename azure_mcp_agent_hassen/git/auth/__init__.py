"""
Git Authentication Package

GitHub OAuth authentication and session management for
secure API access and user authorization.
"""

from .oauth import (
    get_github_login_url,
    initiate_github_login,
    exchange_code_for_token,
    get_authenticated_user,
    store_user_session,
    get_user_session,
    get_all_users,
    revoke_user_session,
    validate_token,
    refresh_user_data
)

__all__ = [
    "get_github_login_url",
    "initiate_github_login",
    "exchange_code_for_token",
    "get_authenticated_user",
    "store_user_session",
    "get_user_session",
    "get_all_users",
    "revoke_user_session",
    "validate_token",
    "refresh_user_data"
]
