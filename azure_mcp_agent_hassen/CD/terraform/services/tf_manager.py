
import os
import subprocess
from ..models.tf_models import TerraformConfig, TerraformStatus
from ..utils.tf_helpers import write_tf_file


def generate_tf_file(config: TerraformConfig, repo_path: str) -> str:
    """Generate a main.tf file in the given repo_path using the config."""
    tf_path = os.path.join(repo_path, 'main.tf')
    write_tf_file(tf_path, config)
    return tf_path

def run_terraform_cmd(cmd: str, cwd: str) -> TerraformStatus:
    try:
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
        return TerraformStatus(status='success' if result.returncode == 0 else 'error', output=result.stdout + result.stderr)
    except Exception as e:
            return TerraformStatus(status='error', message=str(e))

def init(cwd: str) -> TerraformStatus:
    return run_terraform_cmd('terraform init', cwd)

def plan(cwd: str) -> TerraformStatus:
    return run_terraform_cmd('terraform plan', cwd)

def apply(cwd: str, auto_approve: bool = True) -> TerraformStatus:
    cmd = 'terraform apply -auto-approve' if auto_approve else 'terraform apply'
    return run_terraform_cmd(cmd, cwd)

def destroy(cwd: str, auto_approve: bool = True) -> TerraformStatus:
    cmd = 'terraform destroy -auto-approve' if auto_approve else 'terraform destroy'
    return run_terraform_cmd(cmd, cwd)
