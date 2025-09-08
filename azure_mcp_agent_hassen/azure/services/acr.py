"""
Azure Container Registry (ACR) Service
Handles container registry operations for AKS deployment
"""
import subprocess
import json
import logging
from typing import Dict, List, Optional
from ..cli.client import AZ_CMD

# Set up logging
logging.basicConfig(level=logging.DEBUG)


class ACRService:
    """Azure Container Registry management service"""
    
    def __init__(self):
        self.registry_url = None
        
    async def create_acr(self, name: str, resource_group: str, location: str = "eastus") -> Dict:
        """Create Azure Container Registry"""
        try:
            # Create ACR
            cmd = [
                AZ_CMD, "acr", "create",
                "--name", name,
                "--resource-group", resource_group, 
                "--location", location,
                "--sku", "Basic",
                "--admin-enabled", "true",
                "--output", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                acr_info = json.loads(result.stdout)
                self.registry_url = acr_info.get("loginServer")
                
                return {
                    "status": "success",
                    "acr_name": name,
                    "login_server": self.registry_url,
                    "resource_group": resource_group,
                    "sku": "Basic",
                    "admin_enabled": True,
                    "message": f"ACR {name} created successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to create ACR: {result.stderr}",
                    "output": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Exception creating ACR: {str(e)}"
            }
    
    async def get_acr_credentials(self, name: str) -> Dict:
        """Get ACR login credentials"""
        try:
            cmd = [AZ_CMD, "acr", "credential", "show", "--name", name, "--output", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                creds = json.loads(result.stdout)
                return {
                    "status": "success",
                    "username": creds.get("username"),
                    "passwords": creds.get("passwords", []),
                    "registry_url": f"{name}.azurecr.io"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get ACR credentials: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception getting ACR credentials: {str(e)}"
            }
    
    async def login_to_acr(self, name: str) -> Dict:
        """Login to ACR using Azure CLI"""
        try:
            cmd = [AZ_CMD, "acr", "login", "--name", name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Successfully logged into ACR {name}",
                    "registry_url": f"{name}.azurecr.io"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to login to ACR: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception logging into ACR: {str(e)}"
            }
    
    async def push_image_to_acr(self, local_image: str, acr_name: str, repo_name: str, tag: str = "latest") -> Dict:
        """Push Docker image to ACR"""
        logging.info(f"Starting ACR push process for image: {local_image}")
        logging.info(f"ACR name: {acr_name}, repo name: {repo_name}, tag: {tag}")
        
        try:
            acr_url = f"{acr_name}.azurecr.io"
            target_image = f"{acr_url}/{repo_name}:{tag}"
            
            logging.info(f"Target ACR image: {target_image}")
            
            # First, let's check if Docker is running and list available images
            list_cmd = ["docker", "images"]
            list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            logging.info(f"Available Docker images:\n{list_result.stdout}")
            
            if list_result.returncode != 0:
                logging.error(f"Failed to list Docker images: {list_result.stderr}")
                return {
                    "status": "error",
                    "message": f"Docker not available or not running: {list_result.stderr}",
                    "debug_info": {
                        "command": " ".join(list_cmd),
                        "stderr": list_result.stderr,
                        "stdout": list_result.stdout
                    }
                }
            
            # Tag image for ACR
            tag_cmd = ["docker", "tag", local_image, target_image]
            logging.info(f"Executing tag command: {' '.join(tag_cmd)}")
            
            tag_result = subprocess.run(tag_cmd, capture_output=True, text=True, timeout=60)
            logging.info(f"Tag command stdout: {tag_result.stdout}")
            logging.info(f"Tag command stderr: {tag_result.stderr}")
            logging.info(f"Tag command return code: {tag_result.returncode}")
            
            if tag_result.returncode != 0:
                logging.error(f"Failed to tag image: {tag_result.stderr}")
                return {
                    "status": "error",
                    "message": f"Failed to tag image: {tag_result.stderr}",
                    "debug_info": {
                        "local_image": local_image,
                        "target_image": target_image,
                        "command": " ".join(tag_cmd),
                        "stderr": tag_result.stderr,
                        "stdout": tag_result.stdout,
                        "available_images": list_result.stdout
                    }
                }
            
            logging.info("Image tagged successfully, proceeding with push...")
            
            # Push to ACR
            push_cmd = ["docker", "push", target_image]
            logging.info(f"Executing push command: {' '.join(push_cmd)}")
            
            push_result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=600)
            logging.info(f"Push command stdout: {push_result.stdout}")
            logging.info(f"Push command stderr: {push_result.stderr}")
            logging.info(f"Push command return code: {push_result.returncode}")
            
            if push_result.returncode == 0:
                logging.info(f"Successfully pushed {local_image} to ACR as {target_image}")
                return {
                    "status": "success",
                    "local_image": local_image,
                    "acr_image": target_image,
                    "message": f"Successfully pushed {local_image} to ACR as {target_image}",
                    "debug_info": {
                        "push_output": push_result.stdout
                    }
                }
            else:
                logging.error(f"Failed to push to ACR: {push_result.stderr}")
                return {
                    "status": "error",
                    "message": f"Failed to push to ACR: {push_result.stderr}",
                    "debug_info": {
                        "command": " ".join(push_cmd),
                        "stderr": push_result.stderr,
                        "stdout": push_result.stdout
                    }
                }
                
        except Exception as e:
            logging.exception(f"Exception occurred during ACR push: {str(e)}")
            return {
                "status": "error",
                "message": f"Exception pushing to ACR: {str(e)}",
                "debug_info": {
                    "exception_type": type(e).__name__,
                    "local_image": local_image,
                    "acr_name": acr_name,
                    "repo_name": repo_name,
                    "tag": tag
                }
            }
    
    async def list_acr_repositories(self, acr_name: str) -> Dict:
        """List repositories in ACR"""
        try:
            cmd = [AZ_CMD, "acr", "repository", "list", "--name", acr_name, "--output", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                repos = json.loads(result.stdout)
                return {
                    "status": "success",
                    "acr_name": acr_name,
                    "repositories": repos,
                    "count": len(repos)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to list repositories: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception listing repositories: {str(e)}"
            }
    
    async def attach_acr_to_aks(self, acr_name: str, aks_name: str, resource_group: str) -> Dict:
        """Attach ACR to AKS cluster for seamless image pulling"""
        try:
            cmd = [
                AZ_CMD, "aks", "update",
                "--name", aks_name,
                "--resource-group", resource_group,
                "--attach-acr", acr_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"ACR {acr_name} attached to AKS {aks_name}",
                    "acr_name": acr_name,
                    "aks_name": aks_name,
                    "integration": "enabled"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to attach ACR to AKS: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception attaching ACR to AKS: {str(e)}"
            }
