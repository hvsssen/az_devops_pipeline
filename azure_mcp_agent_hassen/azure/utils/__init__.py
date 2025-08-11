"""
Azure Utilities Package

Common utilities and helpers for Azure operations including
session management, monitoring, and data formatting.
"""

from .helpers import (
    format_azure_cost,
    validate_vm_state,
    format_vm_size_info,
    parse_azure_date,
    get_billing_period_dates,
    sanitize_resource_name,
    build_azure_filter
)

from .monitoring import (
    get_resource_metrics,
    get_vm_performance_metrics,
    get_cost_analysis,
    get_resource_health,
    monitor_vm_availability
)

__all__ = [
    # Helper utilities
    "format_azure_cost",
    "validate_vm_state", 
    "format_vm_size_info",
    "parse_azure_date",
    "get_billing_period_dates",
    "sanitize_resource_name",
    "build_azure_filter",
    
    # Monitoring utilities
    "get_resource_metrics",
    "get_vm_performance_metrics", 
    "get_cost_analysis",
    "get_resource_health",
    "monitor_vm_availability"
]
