"""
Azure Services Package

Provides business logic services for Azure operations including
authentication, compute resources, resource management, and monitoring.
"""

from .auth import launch_azure_login, get_azure_subscriptions, azure_health_check
from .compute import (
    get_azure_vm_usage_and_cost,
    get_azure_vm_details
)
from .resources import (
    list_azure_resource_groups,
    create_resource_group,
    delete_resource_group
)

__all__ = [
    # Authentication
    "launch_azure_login",
    "get_azure_subscriptions",
    "azure_health_check",
    
    # Compute services
    "get_azure_vm_usage_and_cost",
    "get_azure_vm_details",
    
    # Resource management
    "list_azure_resource_groups",
    "create_resource_group",
    "delete_resource_group"
]
