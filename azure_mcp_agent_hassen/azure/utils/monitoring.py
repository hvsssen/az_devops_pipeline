"""
Azure Monitoring and Metrics Utilities

Utilities for monitoring Azure resources, collecting metrics,
and handling cost analysis data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..cli.client import az_command


def get_resource_metrics(resource_id: str, metric_names: List[str], 
                        start_time: Optional[str] = None,
                        end_time: Optional[str] = None) -> Dict[str, Any]:
    """Get metrics for a specific Azure resource"""
    try:
        # Default to last 24 hours if no time range specified
        if not start_time:
            start_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        if not end_time:
            end_time = datetime.utcnow().isoformat()
        
        metrics_str = ",".join(metric_names)
        
        result = az_command(
            "monitor", "metrics", "list",
            "--resource", resource_id,
            "--metric", metrics_str,
            "--start-time", start_time,
            "--end-time", end_time,
            "--aggregation", "Average"
        )
        
        return {
            "status": "ok",
            "metrics": result.get("value", []),
            "timespan": f"{start_time} to {end_time}"
        }
        
    except Exception as e:
        logging.error(f"Failed to get resource metrics: {e}")
        return {"status": "error", "error": str(e)}


def get_vm_performance_metrics(vm_name: str, resource_group: str,
                             subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """Get performance metrics for a specific VM"""
    try:
        # Construct resource ID
        if not subscription_id:
            # Get default subscription
            account_info = az_command("account", "show")
            subscription_id = account_info.get("id")
        
        resource_id = (
            f"/subscriptions/{subscription_id}/"
            f"resourceGroups/{resource_group}/"
            f"providers/Microsoft.Compute/virtualMachines/{vm_name}"
        )
        
        # Common VM metrics
        vm_metrics = [
            "Percentage CPU",
            "Network In Total", 
            "Network Out Total",
            "Disk Read Bytes",
            "Disk Write Bytes"
        ]
        
        return get_resource_metrics(resource_id, vm_metrics)
        
    except Exception as e:
        logging.error(f"Failed to get VM performance metrics: {e}")
        return {"status": "error", "error": str(e)}


def get_cost_analysis(subscription_id: Optional[str] = None,
                     resource_group: Optional[str] = None,
                     timeframe: str = "MonthToDate") -> Dict[str, Any]:
    """Get cost analysis for subscription or resource group"""
    try:
        cmd_args = ["costmanagement", "query"]
        
        if resource_group:
            if not subscription_id:
                account_info = az_command("account", "show")
                subscription_id = account_info.get("id")
            
            scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        else:
            if subscription_id:
                scope = f"/subscriptions/{subscription_id}"
            else:
                # Use default subscription
                account_info = az_command("account", "show")
                scope = f"/subscriptions/{account_info.get('id')}"
        
        cmd_args.extend(["--scope", scope])
        cmd_args.extend(["--timeframe", timeframe])
        
        result = az_command(*cmd_args)
        
        return {
            "status": "ok",
            "cost_data": result,
            "scope": scope,
            "timeframe": timeframe
        }
        
    except Exception as e:
        logging.error(f"Failed to get cost analysis: {e}")
        return {"status": "error", "error": str(e)}


def get_resource_health(resource_id: str) -> Dict[str, Any]:
    """Check health status of an Azure resource"""
    try:
        result = az_command(
            "resource", "health", "check",
            "--resource-id", resource_id
        )
        
        return {
            "status": "ok",
            "health_status": result.get("properties", {}).get("currentHealthStatus", "Unknown"),
            "reason": result.get("properties", {}).get("reasonChronicity", "Unknown"),
            "last_updated": result.get("properties", {}).get("occurredTime", "Unknown")
        }
        
    except Exception as e:
        logging.error(f"Failed to check resource health: {e}")
        return {"status": "error", "error": str(e)}


def monitor_vm_availability(vm_name: str, resource_group: str,
                           subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """Monitor VM availability and status"""
    try:
        if not subscription_id:
            account_info = az_command("account", "show")
            subscription_id = account_info.get("id")
        
        # Get VM details
        vm_details = az_command(
            "vm", "show",
            "--name", vm_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        )
        
        # Get instance view for current status
        instance_view = az_command(
            "vm", "get-instance-view",
            "--name", vm_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        )
        
        # Extract status information
        power_state = "Unknown"
        provisioning_state = "Unknown"
        
        for status in instance_view.get("statuses", []):
            if status.get("code", "").startswith("PowerState/"):
                power_state = status.get("code")
            elif status.get("code", "").startswith("ProvisioningState/"):
                provisioning_state = status.get("code")
        
        return {
            "status": "ok",
            "vm_name": vm_name,
            "power_state": power_state,
            "provisioning_state": provisioning_state,
            "location": vm_details.get("location"),
            "vm_size": vm_details.get("hardwareProfile", {}).get("vmSize"),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Failed to monitor VM availability: {e}")
        return {"status": "error", "error": str(e)}
