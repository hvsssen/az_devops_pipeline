"""
Docker Deployment Services

High-level deployment and orchestration services for Docker containers
including automated deployment pipelines and container management.
"""

import os
import logging
from typing import Dict, Any, Optional, List

from ..models import DeployRequest, ContainerRunOptions, PortDetectionResult
from ..engine import build_image, push_image, run_container, docker_login
from ..utils import detect_project_ports, generate_container_name


async def deploy_application(deploy_request: DeployRequest) -> Dict[str, Any]:
    """Complete deployment pipeline for a repository"""
    try:
        deployment_log = []
        
        # Step 1: Docker login
        login_result = docker_login()
        if login_result["status"] != "ok":
            return {"status": "error", "error": f"Docker login failed: {login_result.get('error')}"}
        deployment_log.append("✅ Docker login successful")
        
        # Step 2: Build image
        build_result = build_image(
            repo_path=deploy_request.repo_path,
            image_name=deploy_request.image_name,
            tag=deploy_request.tag
        )
        if build_result["status"] != "ok":
            return {"status": "error", "error": f"Build failed: {build_result.get('error')}"}
        deployment_log.append(f"✅ Built image: {build_result['image']}")
        
        # Step 3: Push image
        push_result = push_image(
            image_name=deploy_request.image_name,
            tag=deploy_request.tag
        )
        if push_result["status"] != "ok":
            return {"status": "error", "error": f"Push failed: {push_result.get('error')}"}
        deployment_log.append(f"✅ Pushed image: {push_result['image']}")
        
        # Step 4: Detect ports for deployment
        port_detection = detect_project_ports(deploy_request.repo_path)
        
        return {
            "status": "success",
            "image": build_result["image"],
            "deployment_log": deployment_log,
            "repo_full_name": deploy_request.repo_full_name,
            "detected_ports": port_detection.detected_ports,
            "message": "Application deployed successfully"
        }
        
    except Exception as e:
        logging.error(f"Deployment failed: {e}")
        return {"status": "error", "error": f"Deployment failed: {str(e)}"}


def deploy_and_run_container(deploy_request: DeployRequest, 
                           port_mappings: Optional[Dict[str, str]] = None,
                           environment: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Deploy application and immediately run container"""
    try:
        # First deploy the application
        deploy_result = deploy_application(deploy_request)
        if deploy_result["status"] != "success":
            return deploy_result
        
        # Detect ports if not provided
        if not port_mappings:
            port_detection = detect_project_ports(deploy_request.repo_path)
            port_mappings = {}
            for port in port_detection.detected_ports[:3]:  # Use first 3 detected ports
                port_mappings[str(port)] = str(port)
        
        # Generate container name
        container_name = generate_container_name(deploy_request.image_name, deploy_request.tag)
        
        # Configure container run options
        run_options = ContainerRunOptions(
            image=deploy_result["image"],
            name=container_name,
            ports=port_mappings or {},
            environment=environment or {},
            detach=True,
            restart_policy="unless-stopped"
        )
        
        # Run container
        run_result = run_container(run_options)
        if run_result["status"] != "ok":
            return {"status": "error", "error": f"Failed to run container: {run_result.get('error')}"}
        
        return {
            "status": "success",
            "image": deploy_result["image"],
            "container_id": run_result["container_id"],
            "container_name": container_name,
            "port_mappings": port_mappings,
            "deployment_log": deploy_result["deployment_log"],
            "message": "Application deployed and running successfully"
        }
        
    except Exception as e:
        logging.error(f"Deploy and run failed: {e}")
        return {"status": "error", "error": f"Deploy and run failed: {str(e)}"}


def create_deployment_plan(repo_path: str, image_name: str) -> Dict[str, Any]:
    """Analyze repository and create deployment plan"""
    try:
        # Detect ports and configuration
        port_detection = detect_project_ports(repo_path)
        
        # Analyze project structure
        from ..utils import detect_project_type
        project_type = detect_project_type(repo_path)
        project_analysis = {
            "framework": project_type,
            "has_dockerfile": os.path.exists(os.path.join(repo_path, "Dockerfile")),
            "has_database": False  # Could be enhanced with more analysis
        }
        
        # Generate deployment recommendations
        recommendations = []
        
        if port_detection.detected_ports:
            recommendations.append(f"Expose ports: {', '.join(map(str, port_detection.detected_ports))}")
        
        if project_analysis.get("has_database"):
            recommendations.append("Consider setting up database connection")
        
        if project_analysis.get("framework") == "node":
            recommendations.append("Set NODE_ENV environment variable")
        elif project_analysis.get("framework") == "python":
            recommendations.append("Consider using production WSGI server")
        
        deployment_plan = {
            "image_name": image_name,
            "detected_ports": port_detection.detected_ports,
            "recommended_ports": port_detection.recommended_ports,
            "project_type": project_analysis.get("framework", "unknown"),
            "has_dockerfile": project_analysis.get("has_dockerfile", False),
            "recommendations": recommendations,
            "estimated_resources": {
                "memory": "512MB",
                "cpu": "0.5 cores"
            }
        }
        
        return {
            "status": "ok",
            "deployment_plan": deployment_plan
        }
        
    except Exception as e:
        logging.error(f"Failed to create deployment plan: {e}")
        return {"status": "error", "error": str(e)}


def scale_application(image_name: str, tag: str, replicas: int) -> Dict[str, Any]:
    """Scale application by running multiple container instances"""
    try:
        from ..engine import list_containers
        
        # Get existing containers for this image
        containers_result = list_containers(all_containers=True)
        if containers_result["status"] != "ok":
            return {"status": "error", "error": "Failed to list containers"}
        
        full_image_name = f"{image_name}:{tag}"
        existing_containers = [
            c for c in containers_result["containers"]
            if c["image"] == full_image_name
        ]
        
        current_replicas = len(existing_containers)
        
        if replicas == current_replicas:
            return {
                "status": "ok",
                "message": f"Application already running with {replicas} replicas",
                "current_replicas": current_replicas
            }
        
        scaling_log = []
        
        if replicas > current_replicas:
            # Scale up - create new containers
            for i in range(replicas - current_replicas):
                container_name = f"{image_name.replace('/', '_')}_{tag}_replica_{current_replicas + i + 1}"
                
                run_options = ContainerRunOptions(
                    image=full_image_name,
                    name=container_name,
                    detach=True,
                    restart_policy="unless-stopped"
                )
                
                run_result = run_container(run_options)
                if run_result["status"] == "ok":
                    scaling_log.append(f"✅ Started replica: {container_name}")
                else:
                    scaling_log.append(f"❌ Failed to start replica: {container_name}")
        
        else:
            # Scale down - stop excess containers
            from ..engine import stop_container, remove_container
            
            containers_to_remove = existing_containers[replicas:]
            for container in containers_to_remove:
                container_id = container["container_id"]
                
                # Stop container
                stop_result = stop_container(container_id)
                if stop_result["status"] == "ok":
                    # Remove container
                    remove_result = remove_container(container_id)
                    if remove_result["status"] == "ok":
                        scaling_log.append(f"✅ Removed replica: {container['name']}")
                    else:
                        scaling_log.append(f"⚠️ Stopped but failed to remove: {container['name']}")
                else:
                    scaling_log.append(f"❌ Failed to stop replica: {container['name']}")
        
        return {
            "status": "ok",
            "message": f"Scaled application to {replicas} replicas",
            "previous_replicas": current_replicas,
            "target_replicas": replicas,
            "scaling_log": scaling_log
        }
        
    except Exception as e:
        logging.error(f"Scaling failed: {e}")
        return {"status": "error", "error": f"Scaling failed: {str(e)}"}
