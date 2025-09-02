
import os
import subprocess
from ..models.tf_models import TerraformConfig, TerraformStatus
from ..utils.tf_helpers import write_tf_file

# Import Azure auth functions
from azure_mcp_agent_hassen.azure.services.auth import get_azure_subscriptions


def check_azure_auth() -> TerraformStatus:
    """Check if user is authenticated with Azure"""
    try:
        auth_result = get_azure_subscriptions()
        if auth_result.status == "not_logged_in":
            return TerraformStatus(
                status='error', 
                message="Azure authentication required. Please run Azure login first."
            )
        elif auth_result.status == "error":
            return TerraformStatus(
                status='error', 
                message=f"Azure authentication error: {auth_result.message}"
            )
        return TerraformStatus(status='success', message="Azure authentication verified")
    except Exception as e:
        return TerraformStatus(
            status='error', 
            message=f"Failed to check Azure authentication: {str(e)}"
        )


def generate_tf_file(config: TerraformConfig, repo_path: str) -> str:
    tf_path = os.path.join(repo_path, 'main.tf')
    write_tf_file(tf_path, config)
    return tf_path

def run_terraform_cmd(cmd: str, cwd: str, check_auth: bool = True) -> TerraformStatus:
    try:
        # Check Azure authentication first (unless disabled)
        if check_auth:
            auth_check = check_azure_auth()
            if auth_check.status != 'success':
                return auth_check
                
        # Check if directory exists
        if not os.path.exists(cwd):
            return TerraformStatus(status='error', message=f"Directory does not exist: {cwd}")
        
        # Check if directory contains terraform files
        tf_files = [f for f in os.listdir(cwd) if f.endswith('.tf')]
        if not tf_files:
            return TerraformStatus(status='error', message=f"No Terraform files found in directory: {cwd}")
            
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
        return TerraformStatus(status='success' if result.returncode == 0 else 'error', output=result.stdout + result.stderr)
    except Exception as e:
        return TerraformStatus(status='error', message=str(e))

def init(cwd: str) -> TerraformStatus:
    return run_terraform_cmd('terraform init', cwd, check_auth=False)  # Init doesn't need Azure auth

def plan(cwd: str) -> TerraformStatus:
    return run_terraform_cmd('terraform plan', cwd, check_auth=True)  # Plan needs Azure auth

def apply(cwd: str, auto_approve: bool = True) -> TerraformStatus:
    cmd = 'terraform apply -auto-approve' if auto_approve else 'terraform apply'
    return run_terraform_cmd(cmd, cwd, check_auth=True)  # Apply needs Azure auth

def destroy(cwd: str, auto_approve: bool = True) -> TerraformStatus:
    cmd = 'terraform destroy -auto-approve' if auto_approve else 'terraform destroy'
    return run_terraform_cmd(cmd, cwd, check_auth=True)  # Destroy needs Azure auth
