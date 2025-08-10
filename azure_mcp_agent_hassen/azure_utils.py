import os
import subprocess
import asyncio
import json
import time
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Azure CLI command based on platform
if platform.system() == "Windows":
    AZ_CMD = r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
else:
    AZ_CMD = "az"

STORAGE_FILE = Path("azure_auth_data.json")

# --- Pydantic Models ---

class AzureSubscription(BaseModel):
    id: str
    name: str
    state: str
    tenantId: str
    isDefault: bool

class AzureVM(BaseModel):
    name: str
    resource_group: str
    location: str
    status: str
    subscription_id: str

class AzureLoginResponse(BaseModel):
    status: str
    message: str
    error: Optional[str] = None

class AzureSubscriptionsResponse(BaseModel):
    status: str
    subscriptions: Optional[List[Dict]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class AzureVMUsageResponse(BaseModel):
    status: str
    vms: List[Dict]
    total_cost: float
    currency: Optional[str]
    debug: List[str]
    vm_error: Optional[str] = None
    cost_error: Optional[str] = None

# --- Utility Functions ---

def az_command(*args) -> Dict[str, Any]:
    """Execute Azure CLI command and return JSON output"""
    env = os.environ.copy()
    result = subprocess.run(
        [AZ_CMD, *args, "--output", "json"],
        capture_output=True,
        text=True,
        env=env
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {str(e)}, stdout: {result.stdout}")
        raise RuntimeError(f"Failed to parse JSON output: {str(e)}, stdout: {result.stdout}")

async def az_command_async(cmd: str) -> str:
    """Execute Azure CLI command asynchronously"""
    args = [AZ_CMD] + cmd.split()
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        return f"❌ Error: {stderr.decode()}"

    return stdout.decode()

def save_azure_session(subscriptions: List[Dict]) -> None:
    """Save Azure session data to file"""
    STORAGE_FILE.write_text(json.dumps(subscriptions, indent=2))
    logging.debug("Azure session saved to file")

def load_azure_session() -> Optional[List[Dict]]:
    """Load Azure session data from file"""
    if STORAGE_FILE.exists():
        return json.loads(STORAGE_FILE.read_text())
    return None

def ensure_cost_extension_installed() -> None:
    """Ensure Azure Cost Management extension is installed"""
    try:
        az_command("extension", "add", "--name", "costmanagement")
        logging.debug("costmanagement extension installed.")
    except RuntimeError as e:
        if "already installed" in str(e):
            logging.debug("costmanagement extension already installed.")
        else:
            logging.error(f"Failed to install costmanagement extension: {e}")

# --- Main Azure Functions ---

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
        sub_id = subscription.get("id")
        logging.debug(f"Using Azure subscription ID: {sub_id}")
        result.debug.append(f"Using subscription ID: {sub_id}")

        # Get all VMs in the subscription
        logging.debug("Fetching Azure VM list")
        result.debug.append("Fetching VM list")
        
        try:
            vms = az_command("vm", "list", "--subscription", sub_id)
            for vm in vms:
                result.vms.append({
                    "name": vm.get("name"),
                    "resource_group": vm.get("resourceGroup"),
                    "location": vm.get("location"),
                    "status": vm.get("powerState", "Unknown"),
                    "subscription_id": sub_id
                })
            logging.debug(f"Found {len(vms)} Azure VMs")
            result.debug.append(f"Found {len(vms)} VMs")
        except RuntimeError as e:
            logging.error(f"Azure VM list failed: {str(e)}")
            result.debug.append(f"VM list failed: {str(e)}")
            result.vm_error = f"Failed to fetch VMs: {str(e)}"

        # Query cost using Azure consumption API
        logging.debug("Fetching Azure cost data")
        result.debug.append("Fetching cost data")
        
        try:
            # Get last 30 days of usage
            time_period_from = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 30 * 24 * 3600))
            time_period_to = time.strftime("%Y-%m-%d", time.gmtime())

            usage_data = az_command(
                "consumption", "usage", "list",
                "--subscription", sub_id,
                "--start-date", time_period_from,
                "--end-date", time_period_to
            )

            total_cost = 0.0
            currency = None
            
            for usage in usage_data:
                try:
                    cost_raw = usage.get("pretaxCost")
                    if cost_raw in [None, "None", ""]:
                        continue
                    cost = float(cost_raw)
                    total_cost += cost
                    if not currency:
                        currency = usage.get("currency")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Skipping invalid cost value: {cost_raw} due to error: {e}")
                    continue

            result.total_cost = total_cost
            result.currency = currency
            logging.debug(f"Total Azure cost: {total_cost} {currency}")
            result.debug.append(f"Total cost: {total_cost} {currency}")

        except RuntimeError as e:
            logging.error(f"Azure cost query failed: {str(e)}")
            result.debug.append(f"Cost query failed: {str(e)}")
            result.cost_error = f"Failed to fetch cost data: {str(e)}"

        return result

    except Exception as e:
        logging.error(f"Unexpected error in Azure VM usage analysis: {str(e)}")
        result.status = "error"
        result.debug.append(f"Unexpected error: {str(e)}")
        return result

def azure_health_check() -> Dict[str, str]:
    """Simple health check for Azure utilities"""
    try:
        return {"status": "ok", "message": "Azure MCP utilities are working"}
    except Exception as e:
        logging.error(f"Azure health check failed: {e}")
        return {"status": "error", "error": str(e)}

# --- Azure Resource Management Functions ---

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
