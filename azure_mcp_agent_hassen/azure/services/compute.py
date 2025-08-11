"""
Azure Virtual Machine Services

Handles Azure VM operations, usage analysis, and cost management.
"""

import logging
from typing import Optional, Dict, Any

from ..models.azure_models import AzureVMUsageResponse
from ..cli.client import az_command, load_azure_session, ensure_cost_extension_installed


def get_azure_vm_usage_and_cost() -> AzureVMUsageResponse:
    """Fetch details and costs of all Azure VMs for the subscription"""
    logging.debug("Starting Azure VM usage and cost analysis")
    
    result = AzureVMUsageResponse(
        status="ok",
        vms=[],
        total_cost=0.0,
        currency=None,
        debug=[]
    )

    try:
        # Load subscriptions
        logging.debug("Loading Azure subscriptions")
        result.debug.append("Loading Azure subscriptions")
        
        subscriptions = load_azure_session()
        if not subscriptions:
            logging.warning("No Azure subscriptions found")
            result.status = "not_logged_in"
            result.debug.append("No subscriptions found - please log in first")
            return result

        # Use the first subscription
        subscription = subscriptions[0]
        subscription_id = subscription.get("id")
        result.debug.append(f"Using subscription: {subscription.get('name')} ({subscription_id})")
        
        # Set subscription context
        az_command("account", "set", "--subscription", subscription_id)
        result.debug.append("Set subscription context")

        # Get VMs
        try:
            vms = az_command("vm", "list", "--show-details")
            result.debug.append(f"Found {len(vms)} VMs")
            result.vms = vms
        except Exception as e:
            result.vm_error = str(e)
            result.debug.append(f"VM list error: {str(e)}")

        # Get cost information
        try:
            ensure_cost_extension_installed()
            
            # Query cost management
            cost_data = az_command(
                "costmanagement", "query",
                "--type", "Usage",
                "--dataset-aggregation", "totalCost=sum",
                "--dataset-grouping", "name=ResourceId,type=Dimension",
                "--time-period", "from=2024-01-01T00:00:00+00:00",
                "--time-period", "to=2024-12-31T23:59:59+00:00"
            )
            
            if cost_data and "properties" in cost_data:
                rows = cost_data["properties"].get("rows", [])
                total_cost = sum(float(row[0]) for row in rows if row and len(row) > 0)
                result.total_cost = total_cost
                result.currency = "USD"  # Default currency
                result.debug.append(f"Retrieved cost data: ${total_cost}")
            else:
                result.debug.append("No cost data available")
                
        except Exception as e:
            result.cost_error = str(e)
            result.debug.append(f"Cost query error: {str(e)}")

        return result

    except Exception as e:
        logging.error(f"Unexpected error in Azure VM usage analysis: {str(e)}")
        result.status = "error"
        result.debug.append(f"Unexpected error: {str(e)}")
        return result


def get_azure_vm_details(vm_name: str, resource_group: str, subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information about a specific Azure VM"""
    try:
        if not subscription_id:
            subscriptions = load_azure_session()
            if not subscriptions:
                return {"status": "not_logged_in", "message": "Please log in first"}
            subscription_id = subscriptions[0].get("id")

        vm_details = az_command(
            "vm", "show",
            "--name", vm_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        )
        
        return {
            "status": "ok",
            "vm_details": {
                "name": vm_details.get("name"),
                "location": vm_details.get("location"),
                "vm_size": vm_details.get("hardwareProfile", {}).get("vmSize"),
                "os_type": vm_details.get("storageProfile", {}).get("osDisk", {}).get("osType"),
                "provisioning_state": vm_details.get("provisioningState"),
                "power_state": vm_details.get("instanceView", {}).get("statuses", [{}])[-1].get("displayStatus")
            }
        }
    except Exception as e:
        logging.error(f"Failed to get Azure VM details: {e}")
        return {"status": "error", "error": str(e)}
