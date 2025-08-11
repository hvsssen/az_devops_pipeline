"""
Azure Resource Management Services

Handles Azure resource groups and general resource operations.
"""

import logging
from typing import Optional, Dict, Any

from ..cli.client import az_command, load_azure_session


def list_azure_resource_groups(subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """List all resource groups in Azure subscription"""
    try:
        if not subscription_id:
            subscriptions = load_azure_session()
            if not subscriptions:
                return {"status": "not_logged_in", "message": "Please log in first"}
            subscription_id = subscriptions[0].get("id")

        resource_groups = az_command("group", "list", "--subscription", subscription_id)
        
        return {
            "status": "ok",
            "resource_groups": [
                {
                    "name": rg.get("name"),
                    "location": rg.get("location"),
                    "subscription_id": subscription_id
                }
                for rg in resource_groups
            ],
            "count": len(resource_groups)
        }
    except Exception as e:
        logging.error(f"Failed to list Azure resource groups: {e}")
        return {"status": "error", "error": str(e)}


def create_resource_group(name: str, location: str, subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new Azure resource group"""
    try:
        if not subscription_id:
            subscriptions = load_azure_session()
            if not subscriptions:
                return {"status": "not_logged_in", "message": "Please log in first"}
            subscription_id = subscriptions[0].get("id")

        result = az_command(
            "group", "create",
            "--name", name,
            "--location", location,
            "--subscription", subscription_id
        )
        
        return {
            "status": "ok",
            "resource_group": {
                "name": result.get("name"),
                "location": result.get("location"),
                "subscription_id": subscription_id
            },
            "message": f"Resource group '{name}' created successfully"
        }
    except Exception as e:
        logging.error(f"Failed to create resource group: {e}")
        return {"status": "error", "error": str(e)}


def delete_resource_group(name: str, subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete an Azure resource group"""
    try:
        if not subscription_id:
            subscriptions = load_azure_session()
            if not subscriptions:
                return {"status": "not_logged_in", "message": "Please log in first"}
            subscription_id = subscriptions[0].get("id")

        az_command(
            "group", "delete",
            "--name", name,
            "--subscription", subscription_id,
            "--yes"  # Auto-confirm deletion
        )
        
        return {
            "status": "ok",
            "message": f"Resource group '{name}' deleted successfully"
        }
    except Exception as e:
        logging.error(f"Failed to delete resource group: {e}")
        return {"status": "error", "error": str(e)}
