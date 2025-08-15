import re
from pathlib import Path
from ..models.tf_models import TerraformConfig

TEMPLATE = '''
provider "azurerm" {{
  features {{}}
}}

resource "azurerm_resource_group" "rg" {{
  name     = "RG-{cluster_name}-{user_id}"
  location = "{region}"
  tags     = {tags_json}
}}

resource "azurerm_kubernetes_cluster" "aks" {{
  name                = "{cluster_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "{dns_prefix}"  # ← Generated from cluster_name

  default_node_pool {{
    name       = "nodepool1"
    node_count = {node_count}
    vm_size    = "{vm_size}"
    os_disk_type = "Ephemeral"
    enable_auto_scaling = {auto_scaling}
    min_count = {min_nodes}
    max_count = {max_nodes}
    type = "VirtualMachineScaleSets"
  }}

  identity {{
    type = "SystemAssigned"
  }}

  private_cluster_enabled = {private_cluster}

  role_based_access_control {{
    enabled = true
  }}

  {oidc_block}

  {monitoring_block}

  auto_upgrade_channel = "stable"

  tags = azurerm_resource_group.rg.tags
}}

output "cluster_name" {{
  value = azurerm_kubernetes_cluster.aks.name
}}

output "resource_group" {{
  value = azurerm_resource_group.rg.name
}}

output "kubeconfig" {{
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}}

output "node_resource_group" {{
  value = azurerm_kubernetes_cluster.aks.node_resource_group
}}
'''

BACKEND_TEMPLATE = '''
terraform {{
  backend "azurerm" {{
    storage_account_name = "mcpstate123"
    container_name       = "tfstate"
    key                  = "{state_key}"
  }}
}}
'''

def write_tf_file(path: str, config: TerraformConfig):
    """
    Writes main.tf and backend.tf based on config.
    Uses cluster_name to generate a valid dns_prefix.
    dns_domain is ignored here (used later in ingress, not in AKS resource).
    """
    path = Path(path)

    # 🔁 If it's a directory, assume we want to write main.tf inside it
    if path.is_dir():
        tf_dir = path
        main_tf_path = tf_dir / "main.tf"
    else:
        # If it's a file, use its parent as the dir
        tf_dir = path.parent
        main_tf_path = path
        
    tf_dir.mkdir(exist_ok=True)

    # ✅ Generate valid dns_prefix from cluster_name
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', config.cluster_name)
    dns_prefix = cleaned[:10].lower()
    if len(dns_prefix) < 3:
        raise ValueError("DNS prefix must be at least 3 characters. Use a longer cluster name.")

    # Build optional blocks
    oidc_block = 'oidc_issuer { enabled = true }' if config.enable_oidc else ''
    
    monitoring_block = f'''
    oms_agent {{
      log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
    }}
    ''' if config.enable_monitoring else ''

    # Add Log Analytics Workspace if monitoring is enabled
    law_block = f'''
resource "azurerm_log_analytics_workspace" "law" {{
  name                = "LAW-{config.cluster_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  retention_in_days   = 30
}}
''' if config.enable_monitoring else ''

    # Format main.tf
    try:
        import json
        tags_json = json.dumps(config.tags)
    except Exception:
        tags_json = str({k: str(v) for k, v in config.tags.items()}).replace("'", '"')

    main_content = TEMPLATE.format(
        cluster_name=config.cluster_name,
        user_id=config.user_id,
        region=config.region,
        node_count=config.node_count,
        vm_size=config.vm_size,
        auto_scaling=str(config.auto_scaling).lower(),
        min_nodes=config.min_nodes,
        max_nodes=config.max_nodes,
        private_cluster=str(config.private_cluster).lower(),
        dns_prefix=dns_prefix,
        tags_json=tags_json,
        oidc_block=oidc_block,
        monitoring_block=monitoring_block + law_block
    )
    print(f"Writing Terraform config to {main_tf_path}")
    # Write main.tf
    with open(path, 'w') as f:
        f.write(main_content.strip())

    # Write backend.tf
    backend_path = tf_dir / "backend.tf"
    state_key = f"{config.user_id}-{config.cluster_name}.tfstate"
    with open(backend_path, 'w') as f:
        f.write(BACKEND_TEMPLATE.format(state_key=state_key))

    return str(path)