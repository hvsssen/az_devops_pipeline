"""
Azure Package

Comprehensive Azure cloud management package providing modular access to
Azure CLI operations, resource management, and monitoring capabilities.

This package provides a clean, modular interface for:
- Azure authentication and session management
- Virtual machine operations and monitoring  
- Resource group and subscription management
- Cost analysis and billing information
- Performance metrics and health monitoring
"""

# Core models
from .models import (
    AzureSubscriptionsResponse,
    AzureVMUsageResponse,
    AzureResourceGroup,
    AzureLoginResponse,
    AzureHealthResponse,
    AzureResourceGroupsResponse,
    AzureVMDetailsResponse,
    VMInstanceView,
    AzureCostEntry,
    AzureMetric
)

# CLI client
from .cli import az_command, load_azure_session, save_azure_session ,az_command_async

# Services
from .services import (
    launch_azure_login,
    get_azure_subscriptions,
    azure_health_check,
    get_azure_vm_usage_and_cost,
    get_azure_vm_details,
    list_azure_resource_groups,
    create_resource_group,
    delete_resource_group
)

# Utilities
from .utils import (
    format_azure_cost,
    validate_vm_state,
    format_vm_size_info,
    get_vm_performance_metrics,
    get_cost_analysis,
    monitor_vm_availability
)

__all__ = [
    # Models
    "AzureSubscription",
    "AzureVM", 
    "AzureResourceGroup",
    "VMInstanceView",
    "AzureCostEntry",
    "AzureMetric",
    
    # CLI operations
    "az_command",
    "load_azure_session",
    "save_azure_session",
    
    # Authentication services
    "login_to_azure",
    "check_azure_login_status",
    
    # VM services
    "list_azure_vms",
    "get_vm_details",
    "get_vm_usage_and_cost", 
    "start_vm",
    "stop_vm",
    "restart_vm",
    
    # Resource management
    "list_azure_resource_groups",
    "create_resource_group",
    "delete_resource_group",
    
    # Utilities and monitoring
    "format_azure_cost",
    "validate_vm_state",
    "format_vm_size_info",
    "get_vm_performance_metrics",
    "get_cost_analysis", 
    "monitor_vm_availability"
]

__version__ = "1.0.0"
__author__ = "Azure MCP DevOps Agent"
__description__ = "Modular Azure cloud management package"
