terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "RG-test-cluster-test123"
  location = "East US"
  tags     = {"env": "test", "project": "terraform-test"}
}


resource "azurerm_log_analytics_workspace" "law" {
  name                = "LAW-test-cluster"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  retention_in_days   = 30
  tags                = azurerm_resource_group.rg.tags
}


resource "azurerm_kubernetes_cluster" "aks" {
  name                = "test-cluster"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "testcluste"

  default_node_pool {
    name       = "nodepool1"
    node_count = 3
    vm_size    = "Standard_DS2_v2"
    
    enable_auto_scaling = true
    min_count          = 1
    max_count          = 5
  }

  identity {
    type = "SystemAssigned"
  }

  private_cluster_enabled = false
  role_based_access_control_enabled = true

  oidc_issuer { enabled = true }

  
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  }

  tags = azurerm_resource_group.rg.tags
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "kubeconfig" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}

output "node_resource_group" {
  value = azurerm_kubernetes_cluster.aks.node_resource_group
}