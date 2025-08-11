"""
Azure Data Models

Pydantic models for Azure resources, subscriptions, VMs, and API responses.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel


class AzureSubscription(BaseModel):
    """Model for Azure subscription information"""
    id: str
    name: str
    state: str
    tenantId: str
    isDefault: bool


class AzureVM(BaseModel):
    """Model for Azure Virtual Machine information"""
    name: str
    resource_group: str
    location: str
    status: str
    subscription_id: str


class AzureResourceGroup(BaseModel):
    """Model for Azure Resource Group information"""
    name: str
    location: str
    subscription_id: str
    managed_by: Optional[str] = None


class AzureLoginResponse(BaseModel):
    """Response model for Azure login operations"""
    status: str
    message: str
    error: Optional[str] = None


class AzureSubscriptionsResponse(BaseModel):
    """Response model for Azure subscriptions list"""
    status: str
    subscriptions: Optional[List[Dict]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class AzureVMUsageResponse(BaseModel):
    """Response model for Azure VM usage and cost information"""
    status: str
    vms: List[Dict]
    total_cost: float
    currency: Optional[str]
    debug: List[str]
    vm_error: Optional[str] = None
    cost_error: Optional[str] = None


class AzureHealthResponse(BaseModel):
    """Response model for Azure health check"""
    status: str
    cli_available: bool
    logged_in: bool
    message: str


class AzureResourceGroupsResponse(BaseModel):
    """Response model for Azure resource groups list"""
    status: str
    resource_groups: Optional[List[Dict]] = None
    subscription_id: Optional[str] = None
    error: Optional[str] = None


class AzureVMDetailsResponse(BaseModel):
    """Response model for detailed Azure VM information"""
    status: str
    vm_details: Optional[Dict] = None
    vm_name: str
    resource_group: str
    error: Optional[str] = None


class VMInstanceView(BaseModel):
    """Model for Azure VM instance view"""
    status: str
    power_state: Optional[str] = None
    provisioning_state: Optional[str] = None


class AzureCostEntry(BaseModel):
    """Model for Azure cost information"""
    service_name: str
    meter_category: str
    cost: float
    currency: str
    date: str


class AzureMetric(BaseModel):
    """Model for Azure metrics"""
    name: str
    value: float
    unit: str
    timestamp: str
