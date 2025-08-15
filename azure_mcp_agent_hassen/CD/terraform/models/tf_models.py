from pydantic import BaseModel, Field
from typing import Dict, Optional

class TerraformConfig(BaseModel):
    user_id: str
    cluster_name: str
    region: str
    node_count: int
    vm_size: str
    auto_scaling: bool
    min_nodes: int
    max_nodes: int
    enable_monitoring: bool
    private_cluster: bool
    dns_domain: str
    enable_oidc: bool
    tags: Dict[str, str]

class TerraformStatus(BaseModel):
    status: str
    message: Optional[str] = None
    output: Optional[str] = None

class TerraformGenerateRequest(BaseModel):
    repo_path: str
    config: TerraformConfig