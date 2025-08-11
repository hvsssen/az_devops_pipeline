"""
Azure Authentication Services

Handles Azure login, session management, and authentication status.
"""

import subprocess
import logging
from typing import Optional

from ..models.azure_models import AzureLoginResponse, AzureSubscriptionsResponse
from ..cli.client import az_command, save_azure_session, load_azure_session, AZ_CMD


def launch_azure_login() -> AzureLoginResponse:
    """Launch Azure CLI login process"""
    try:
        subprocess.Popen(f'start "" "{AZ_CMD}" login', shell=True)
        logging.debug("Azure login window launched")
        return AzureLoginResponse(
            status="launched", 
            message="Azure login window opened. Please complete authentication in the browser."
        )
    except Exception as e:
        logging.error(f"Failed to launch Azure login: {e}")
        return AzureLoginResponse(
            status="error", 
            message="Failed to launch login window",
            error=str(e)
        )


def get_azure_subscriptions() -> AzureSubscriptionsResponse:
    """Get list of Azure subscriptions"""
    try:
        # Check if user is logged in
        check_login = subprocess.run(
            [AZ_CMD, "account", "show"],
            capture_output=True,
            text=True
        )
        logging.debug("Checked Azure login status")

        if check_login.returncode != 0:
            logging.warning("User is NOT logged in to Azure")
            return AzureSubscriptionsResponse(
                status="not_logged_in",
                message="Azure login not complete. Please run launch_azure_login() first."
            )

        logging.debug("User is logged in to Azure. Listing subscriptions...")

        # List subscriptions
        subscriptions = az_command("account", "list")
        logging.debug(f"Retrieved {len(subscriptions)} Azure subscriptions")

        # Save session to file
        save_azure_session(subscriptions)

        return AzureSubscriptionsResponse(
            status="ok",
            subscriptions=subscriptions,
            message=f"Successfully retrieved {len(subscriptions)} subscriptions"
        )

    except Exception as e:
        logging.exception("Error occurred during get_azure_subscriptions")
        return AzureSubscriptionsResponse(
            status="error",
            error=str(e),
            message="Failed to retrieve Azure subscriptions"
        )


def azure_health_check() -> dict:
    """Simple health check for Azure utilities"""
    try:
        return {"status": "ok", "message": "Azure MCP utilities are working"}
    except Exception as e:
        logging.error(f"Azure health check failed: {e}")
        return {"status": "error", "error": str(e)}
