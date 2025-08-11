"""
Azure Models Package

Pydantic models for Azure resources and API responses.
"""

from .azure_models import (
    AzureSubscription,
    AzureVM,
    AzureResourceGroup,
    AzureLoginResponse,
    AzureSubscriptionsResponse,
    AzureVMUsageResponse,
    AzureHealthResponse,
    AzureResourceGroupsResponse,
    AzureVMDetailsResponse,
    VMInstanceView,
    AzureCostEntry,
    AzureMetric
)

__all__ = [
    "AzureSubscription",
    "AzureVM",
    "AzureResourceGroup",
    "AzureLoginResponse",
    "AzureSubscriptionsResponse",
    "AzureVMUsageResponse",
    "AzureHealthResponse",
    "AzureResourceGroupsResponse",
    "AzureVMDetailsResponse",
    "VMInstanceView",
    "AzureCostEntry",
    "AzureMetric"
]
