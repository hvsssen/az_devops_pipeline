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


# ACR (Azure Container Registry) Models
class ACRRepository(BaseModel):
    """Model for Azure Container Registry repository"""
    name: str
    tag_count: int
    manifest_count: int
    last_update_time: Optional[str] = None


class ACRInfo(BaseModel):
    """Model for Azure Container Registry information"""
    name: str
    resource_group: str
    login_server: str
    sku: str
    admin_enabled: bool
    location: str
    creation_date: Optional[str] = None


class ACRCredentials(BaseModel):
    """Model for ACR login credentials"""
    username: str
    password: str
    password2: str
    registry_url: str


# Helm Models
class HelmChart(BaseModel):
    """Model for Helm chart information"""
    name: str
    version: str
    app_version: str
    description: str
    chart_path: str


class HelmRelease(BaseModel):
    """Model for Helm release information"""
    name: str
    namespace: str
    revision: int
    updated: str
    status: str
    chart: str
    app_version: str


# Deployment Models
class DeploymentConfig(BaseModel):
    """Model for complete deployment configuration"""
    terraform_config: Dict
    repo_path: str
    image_name: str
    image_tag: str = "latest"
    app_port: int = 80
    registry_choice: str = "acr"  # "acr" or "dockerhub"
    docker_username: Optional[str] = None
    acr_name: Optional[str] = None
    app_name: Optional[str] = None
    namespace: str = "default"
    replica_count: int = 2


class DeploymentResult(BaseModel):
    """Model for deployment result"""
    status: str
    steps: Dict
    overall_success: bool
    message: str
    endpoints: Optional[List[Dict]] = None
