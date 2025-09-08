import re
import logging
from pathlib import Path
from ..models.tf_models import TerraformConfig

# Set up logging
logging.basicConfig(level=logging.DEBUG)

TEMPLATE = '''
terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

data "azurerm_resource_group" "rg" {{
  name = "{existing_resource_group}"
}}

{law_block}

resource "azurerm_kubernetes_cluster" "aks" {{
  name                = "{cluster_name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  dns_prefix          = "{dns_prefix}"

  default_node_pool {{
    name       = "nodepool1"
    node_count = {node_count}
    vm_size    = "{vm_size}"
    {auto_scaling_block}
  }}

  identity {{
    type = "SystemAssigned"
  }}

  private_cluster_enabled = {private_cluster}
  role_based_access_control_enabled = true

  {oidc_block}

  {monitoring_block}

  tags = data.azurerm_resource_group.rg.tags
}}

output "cluster_name" {{
  value = azurerm_kubernetes_cluster.aks.name
}}

output "resource_group" {{
  value = data.azurerm_resource_group.rg.name
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
    storage_account_name = "{storage_account_name}"
    container_name       = "tfstate"
    key                  = "{state_key}"
    use_azuread_auth     = true
  }}
}}
'''

def write_tf_file(path: str, config: TerraformConfig, use_remote_backend: bool = True):
    """Write Terraform configuration files with comprehensive logging"""
    logging.info(f"Starting Terraform file generation")
    logging.info(f"Path: {path}")
    logging.info(f"Config: {config}")
    logging.info(f"Use remote backend: {use_remote_backend}")
    
    path = Path(path)

    if path.is_dir():
        tf_dir = path
        main_tf_path = tf_dir / "main.tf"
        logging.info(f"Using directory mode - TF dir: {tf_dir}, main.tf: {main_tf_path}")
    else:
        tf_dir = path.parent
        main_tf_path = path
        logging.info(f"Using file mode - TF dir: {tf_dir}, main.tf: {main_tf_path}")
        
    tf_dir.mkdir(exist_ok=True)
    logging.info(f"Created/ensured directory exists: {tf_dir}")
    
    # Check for existing files
    existing_files = list(tf_dir.glob("*.tf"))
    logging.info(f"Existing .tf files in directory: {existing_files}")
    
    # Remove existing backend.tf if we're not using remote backend
    backend_tf_path = tf_dir / "backend.tf"
    if not use_remote_backend and backend_tf_path.exists():
        logging.info(f"Removing existing backend.tf file: {backend_tf_path}")
        backend_tf_path.unlink()
    elif backend_tf_path.exists():
        logging.info(f"Existing backend.tf found: {backend_tf_path}")
        try:
            with open(backend_tf_path, 'r') as f:
                backend_content = f.read()
                logging.info(f"Existing backend.tf content:\n{backend_content}")
        except Exception as e:
            logging.warning(f"Could not read existing backend.tf: {e}")

    cleaned = re.sub(r'[^a-zA-Z0-9]', '', config.cluster_name)
    dns_prefix = cleaned[:10].lower()
    if len(dns_prefix) < 3:
        raise ValueError("DNS prefix must be at least 3 characters. Use a longer cluster name.")

    oidc_block = '''
  oidc_issuer_enabled = true
  workload_identity_enabled = true''' if config.enable_oidc else ''
    
    # Auto-scaling configuration
    auto_scaling_block = f'''
    enable_auto_scaling = true
    min_count          = {config.min_nodes}
    max_count          = {config.max_nodes}''' if config.auto_scaling else ''
    
    monitoring_block = '''
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  }''' if config.enable_monitoring else ''

    law_block = f'''
resource "azurerm_log_analytics_workspace" "law" {{
  name                = "LAW-{config.cluster_name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  retention_in_days   = 30
  tags                = data.azurerm_resource_group.rg.tags
}}
''' if config.enable_monitoring else ''

    try:
        import json
        tags_json = json.dumps(config.tags)
    except Exception:
        tags_json = str({k: str(v) for k, v in config.tags.items()}).replace("'", '"')

    # Default to rg-mcp-devops if no existing resource group specified
    existing_resource_group = getattr(config, 'existing_resource_group', 'rg-mcp-devops')

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
        monitoring_block=monitoring_block,
        law_block=law_block,
        auto_scaling_block=auto_scaling_block,
        existing_resource_group=existing_resource_group
    )
    print(f"Writing Terraform config to {main_tf_path}")
    with open(main_tf_path, 'w', encoding='utf-8') as f:
        f.write(main_content.strip())

    # Only create backend.tf if remote backend is requested
    if use_remote_backend:
        backend_path = tf_dir / "backend.tf"
        state_key = f"{config.user_id}-{config.cluster_name}.tfstate"
        
        # Generate a unique storage account name (must be globally unique)
        import hashlib
        import time
        unique_suffix = hashlib.md5(f"{config.user_id}-{config.cluster_name}-{int(time.time())}".encode()).hexdigest()[:8]
        storage_account_name = f"tfstate{config.user_id.lower().replace('-', '').replace('_', '')[:8]}{unique_suffix}"
        
        # Ensure storage account name is valid (3-24 chars, alphanumeric only)
        storage_account_name = storage_account_name[:24]
        
        with open(backend_path, 'w', encoding='utf-8') as f:
            f.write(BACKEND_TEMPLATE.format(
                state_key=state_key,
                storage_account_name=storage_account_name
            ))
        print(f"Created backend configuration at {backend_path} with storage account: {storage_account_name}")
    else:
        print("Skipping remote backend configuration - using local state")

    return str(main_tf_path)