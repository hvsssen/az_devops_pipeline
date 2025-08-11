"""
Azure CLI Package

Azure CLI command execution and session management utilities.
"""

from .client import (
    az_command,
    az_command_async,
    save_azure_session,
    load_azure_session,
    ensure_cost_extension_installed,
    check_azure_cli_available,
    check_azure_login_status
)

__all__ = [
    "az_command",
    "az_command_async",
    "save_azure_session",
    "load_azure_session",
    "ensure_cost_extension_installed",
    "check_azure_cli_available",
    "check_azure_login_status"
]
