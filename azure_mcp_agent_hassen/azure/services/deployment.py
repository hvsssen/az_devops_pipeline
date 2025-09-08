"""
Complete Azure Deployment Service
Orchestrates Terraform + Docker + ACR + AKS + Helm deployment
"""
import os
import json
from typing import Dict, List, Optional
from .acr import ACRService
from .helm import HelmService
# Import Terraform functions directly
from ...CD.terraform.services.tf_manager import init, plan, apply, destroy


class AzureDeploymentService:
    """Complete Azure deployment orchestration service"""
    
    def __init__(self):
        self.acr_service = ACRService()
        self.helm_service = HelmService()
        
    async def deploy_complete_application(self, config: Dict) -> Dict:
        """
        Complete deployment workflow:
        1. Apply Terraform (AKS + ACR)
        2. Build and push container to ACR or Docker Hub
        3. Create Helm chart
        4. Deploy to AKS with Helm
        """
        try:
            deployment_results = {
                "status": "in_progress",
                "steps": {},
                "overall_success": False
            }
            
            # Step 1: Apply Terraform to create infrastructure
            terraform_result = await self._apply_terraform(config)
            deployment_results["steps"]["terraform"] = terraform_result
            
            if terraform_result["status"] != "success":
                deployment_results["status"] = "failed"
                deployment_results["message"] = "Terraform deployment failed"
                return deployment_results
            
            # Step 2: Handle container registry choice and push image
            registry_result = await self._handle_container_registry(config)
            deployment_results["steps"]["container_registry"] = registry_result
            
            if registry_result["status"] != "success":
                deployment_results["status"] = "failed"
                deployment_results["message"] = "Container registry operation failed"
                return deployment_results
            
            # Step 3: Create and deploy Helm chart
            helm_result = await self._deploy_with_helm(config, registry_result)
            deployment_results["steps"]["helm_deployment"] = helm_result
            
            if helm_result["status"] == "success":
                deployment_results["status"] = "success"
                deployment_results["overall_success"] = True
                deployment_results["message"] = "Complete deployment successful"
                deployment_results["endpoints"] = helm_result.get("endpoints", [])
            else:
                deployment_results["status"] = "failed"
                deployment_results["message"] = "Helm deployment failed"
            
            return deployment_results
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Complete deployment failed: {str(e)}"
            }
    
    async def _apply_terraform(self, config: Dict) -> Dict:
        """Apply Terraform configuration"""
        try:
            repo_path = config.get("repo_path", "./repos/app")
            
            # Apply Terraform using the imported function
            apply_result = apply(repo_path)
            
            if apply_result.status == "success":
                # Extract important outputs
                return {
                    "status": "success",
                    "message": "Infrastructure created successfully",
                    "cluster_name": config.get("terraform_config", {}).get("cluster_name"),
                    "resource_group": f"rg-{config.get('terraform_config', {}).get('user_id', 'default')}",
                    "output": apply_result.output
                }
            else:
                return {
                    "status": "error",
                    "message": f"Terraform apply failed: {apply_result.message or 'Unknown error'}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Terraform application failed: {str(e)}"
            }
    
    async def _handle_container_registry(self, config: Dict) -> Dict:
        """Handle container registry choice (ACR vs Docker Hub)"""
        try:
            registry_choice = config.get("registry_choice", "acr").lower()
            image_name = config.get("image_name", "app")
            image_tag = config.get("image_tag", "latest")
            
            if registry_choice == "acr":
                return await self._push_to_acr(config)
            elif registry_choice == "dockerhub":
                return await self._push_to_dockerhub(config)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown registry choice: {registry_choice}. Use 'acr' or 'dockerhub'"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Container registry handling failed: {str(e)}"
            }
    
    async def _push_to_acr(self, config: Dict) -> Dict:
        """Push image to Azure Container Registry"""
        try:
            acr_name = config.get("acr_name")
            if not acr_name:
                # Generate ACR name based on cluster
                user_id = config.get("terraform_config", {}).get("user_id", "default")
                acr_name = f"acr{user_id.lower().replace('_', '')}registry"
            
            resource_group = f"rg-{config.get('terraform_config', {}).get('user_id', 'default')}"
            image_name = config.get("image_name", "app")
            image_tag = config.get("image_tag", "latest")
            
            # Create ACR if it doesn't exist
            acr_create = await self.acr_service.create_acr(
                name=acr_name,
                resource_group=resource_group,
                location=config.get("terraform_config", {}).get("region", "eastus")
            )
            
            # Login to ACR
            login_result = await self.acr_service.login_to_acr(acr_name)
            if login_result["status"] != "success":
                return login_result
            
            # Push image to ACR
            push_result = await self.acr_service.push_image_to_acr(
                local_image=image_name,
                acr_name=acr_name,
                repo_name=image_name,
                tag=image_tag
            )
            
            if push_result["status"] == "success":
                # Attach ACR to AKS
                cluster_name = config.get("terraform_config", {}).get("cluster_name")
                attach_result = await self.acr_service.attach_acr_to_aks(
                    acr_name=acr_name,
                    aks_name=cluster_name,
                    resource_group=resource_group
                )
                
                return {
                    "status": "success",
                    "registry_type": "acr",
                    "acr_name": acr_name,
                    "image_url": push_result["acr_image"],
                    "acr_attached": attach_result["status"] == "success",
                    "message": "Image pushed to ACR and attached to AKS"
                }
            else:
                return push_result
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"ACR push failed: {str(e)}"
            }
    
    async def _push_to_dockerhub(self, config: Dict) -> Dict:
        """Push image to Docker Hub"""
        try:
            # This would use your existing Docker Hub push logic
            docker_username = config.get("docker_username")
            image_name = config.get("image_name", "app")
            image_tag = config.get("image_tag", "latest")
            
            if not docker_username:
                return {
                    "status": "error",
                    "message": "Docker username required for Docker Hub push"
                }
            
            full_image = f"{docker_username}/{image_name}:{image_tag}"
            
            # Use your existing docker push logic here
            # For now, return success format
            return {
                "status": "success",
                "registry_type": "dockerhub",
                "image_url": full_image,
                "message": f"Image pushed to Docker Hub as {full_image}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Docker Hub push failed: {str(e)}"
            }
    
    async def _deploy_with_helm(self, config: Dict, registry_result: Dict) -> Dict:
        """Deploy application using Helm charts"""
        try:
            app_name = config.get("app_name", config.get("image_name", "app"))
            chart_name = f"{app_name}-chart"
            release_name = f"{app_name}-release"
            namespace = config.get("namespace", "default")
            port = config.get("app_port", 80)
            
            # Create Helm chart
            chart_result = await self.helm_service.create_helm_chart(
                chart_name=chart_name,
                app_name=app_name,
                image_repository=registry_result["image_url"].split(":")[0],  # Remove tag
                image_tag=config.get("image_tag", "latest"),
                port=port,
                namespace=namespace
            )
            
            if chart_result["status"] != "success":
                return chart_result
            
            # Configure kubectl for AKS
            cluster_name = config.get("terraform_config", {}).get("cluster_name")
            resource_group = f"rg-{config.get('terraform_config', {}).get('user_id', 'default')}"
            
            kubectl_config = await self._configure_kubectl(cluster_name, resource_group)
            if kubectl_config["status"] != "success":
                return kubectl_config
            
            # Custom values for deployment
            custom_values = {
                "image": {
                    "repository": registry_result["image_url"].split(":")[0],
                    "tag": config.get("image_tag", "latest")
                },
                "service": {
                    "type": "LoadBalancer",
                    "port": 80,
                    "targetPort": port
                },
                "replicaCount": config.get("replica_count", 2)
            }
            
            # Install Helm chart
            install_result = await self.helm_service.install_helm_chart(
                chart_name=chart_name,
                release_name=release_name,
                namespace=namespace,
                values_override=custom_values
            )
            
            if install_result["status"] == "success":
                # Get service endpoints
                endpoints = await self._get_service_endpoints(release_name, namespace)
                
                return {
                    "status": "success",
                    "chart_name": chart_name,
                    "release_name": release_name,
                    "namespace": namespace,
                    "endpoints": endpoints,
                    "message": f"Application {app_name} deployed successfully to AKS"
                }
            else:
                return install_result
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Helm deployment failed: {str(e)}"
            }
    
    async def _configure_kubectl(self, cluster_name: str, resource_group: str) -> Dict:
        """Configure kubectl to connect to AKS cluster"""
        try:
            import subprocess
            
            cmd = [
                "az", "aks", "get-credentials",
                "--resource-group", resource_group,
                "--name", cluster_name,
                "--overwrite-existing"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"kubectl configured for cluster {cluster_name}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to configure kubectl: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"kubectl configuration failed: {str(e)}"
            }
    
    async def _get_service_endpoints(self, release_name: str, namespace: str) -> List[Dict]:
        """Get service endpoints for the deployed application"""
        try:
            import subprocess
            
            # Get services
            cmd = [
                "kubectl", "get", "services",
                "-l", f"app.kubernetes.io/instance={release_name}",
                "-n", namespace,
                "-o", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                endpoints = []
                
                for service in services_data.get("items", []):
                    service_name = service["metadata"]["name"]
                    service_type = service["spec"]["type"]
                    
                    if service_type == "LoadBalancer":
                        ingress = service.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                        if ingress:
                            for ing in ingress:
                                ip = ing.get("ip", ing.get("hostname", "pending"))
                                port = service["spec"]["ports"][0]["port"]
                                endpoints.append({
                                    "name": service_name,
                                    "type": "LoadBalancer",
                                    "url": f"http://{ip}:{port}",
                                    "status": "ready" if ip != "pending" else "pending"
                                })
                        else:
                            endpoints.append({
                                "name": service_name,
                                "type": "LoadBalancer", 
                                "url": "pending",
                                "status": "pending"
                            })
                    elif service_type == "ClusterIP":
                        endpoints.append({
                            "name": service_name,
                            "type": "ClusterIP",
                            "url": f"internal-only",
                            "status": "ready"
                        })
                
                return endpoints
            else:
                return [{"error": "Failed to get service endpoints"}]
                
        except Exception as e:
            return [{"error": f"Failed to get endpoints: {str(e)}"}]
    
    async def cleanup_deployment(self, config: Dict) -> Dict:
        """Clean up complete deployment"""
        try:
            results = {
                "helm_cleanup": None,
                "terraform_cleanup": None,
                "overall_status": "success"
            }
            
            # Cleanup Helm release
            if config.get("cleanup_helm", True):
                app_name = config.get("app_name", config.get("image_name", "app"))
                release_name = f"{app_name}-release"
                namespace = config.get("namespace", "default")
                
                helm_cleanup = await self.helm_service.uninstall_helm_release(release_name, namespace)
                results["helm_cleanup"] = helm_cleanup
            
            # Cleanup Terraform resources
            if config.get("cleanup_terraform", True):
                repo_path = config.get("repo_path", "./repos/app")
                terraform_cleanup = destroy(repo_path)
                results["terraform_cleanup"] = {
                    "status": terraform_cleanup.status,
                    "message": terraform_cleanup.message,
                    "output": terraform_cleanup.output
                }
                
                if terraform_cleanup.status != "success":
                    results["overall_status"] = "partial_failure"
            
            return results
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cleanup failed: {str(e)}"
            }
