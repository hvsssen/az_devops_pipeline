
import os
import subprocess
import logging
from ..models.tf_models import TerraformConfig, TerraformStatus
from ..utils.tf_helpers import write_tf_file

# Import Azure auth functions
from azure_mcp_agent_hassen.azure.services.auth import get_azure_subscriptions

# Set up logging
logging.basicConfig(level=logging.DEBUG)


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
    """Run terraform command with comprehensive logging"""
    logging.info(f"Starting Terraform command: {cmd}")
    logging.info(f"Working directory: {cwd}")
    logging.info(f"Check auth: {check_auth}")
    
    try:
        # Check Azure authentication first (unless disabled)
        if check_auth:
            logging.info("Checking Azure authentication...")
            auth_check = check_azure_auth()
            logging.info(f"Auth check result: {auth_check.status} - {auth_check.message}")
            if auth_check.status != 'success':
                return auth_check
                
        # Check if directory exists
        if not os.path.exists(cwd):
            logging.error(f"Directory does not exist: {cwd}")
            return TerraformStatus(status='error', message=f"Directory does not exist: {cwd}")
        
        logging.info(f"Directory exists: {cwd}")
        
        # List all files in directory for debugging
        try:
            all_files = os.listdir(cwd)
            logging.info(f"Files in directory: {all_files}")
        except Exception as e:
            logging.warning(f"Could not list directory contents: {e}")
        
        # Check if directory contains terraform files
        tf_files = [f for f in os.listdir(cwd) if f.endswith('.tf')]
        logging.info(f"Terraform files found: {tf_files}")
        
        if not tf_files:
            logging.error(f"No Terraform files found in directory: {cwd}")
            return TerraformStatus(status='error', message=f"No Terraform files found in directory: {cwd}")
        
        # Check for existing .terraform directory and state
        terraform_dir = os.path.join(cwd, '.terraform')
        terraform_state = os.path.join(cwd, 'terraform.tfstate')
        terraform_lock = os.path.join(cwd, '.terraform.lock.hcl')
        
        logging.info(f".terraform directory exists: {os.path.exists(terraform_dir)}")
        logging.info(f"terraform.tfstate exists: {os.path.exists(terraform_state)}")
        logging.info(f".terraform.lock.hcl exists: {os.path.exists(terraform_lock)}")
        
        # Read main.tf content for debugging
        main_tf_path = os.path.join(cwd, 'main.tf')
        if os.path.exists(main_tf_path):
            try:
                with open(main_tf_path, 'r') as f:
                    content = f.read()
                    logging.info(f"main.tf content preview (first 500 chars):\n{content[:500]}")
                    
                    # Check for backend configuration
                    if 'backend' in content:
                        logging.warning("Backend configuration detected in main.tf")
                        backend_start = content.find('backend')
                        backend_section = content[backend_start:backend_start+300]
                        logging.info(f"Backend section: {backend_section}")
                    else:
                        logging.info("No backend configuration found in main.tf")
                        
            except Exception as e:
                logging.warning(f"Could not read main.tf: {e}")
        
        # Run the terraform command
        logging.info(f"Executing command: {cmd}")
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=300)
        
        logging.info(f"Command return code: {result.returncode}")
        logging.info(f"Command stdout: {result.stdout}")
        if result.stderr:
            logging.warning(f"Command stderr: {result.stderr}")
        
        status = 'success' if result.returncode == 0 else 'error'
        output = result.stdout + result.stderr
        
        return TerraformStatus(
            status=status, 
            output=output,
            message=f"Command completed with status: {status}"
        )
        
    except subprocess.TimeoutExpired:
        logging.error("Terraform command timed out")
        return TerraformStatus(status='error', message="Terraform command timed out after 5 minutes")
    except Exception as e:
        logging.exception(f"Exception in run_terraform_cmd: {str(e)}")
        return TerraformStatus(
            status='error', 
            message=f"Exception running terraform command: {str(e)}",
            output=f"Exception: {str(e)}"
        )

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
