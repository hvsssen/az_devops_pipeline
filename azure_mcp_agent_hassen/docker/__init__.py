"""
Docker Package

Comprehensive Docker container management package providing modular access to
Docker engine operations, deployment services, and container orchestration.

This package provides a clean, modular interface for:
- Docker engine operations (build, push, pull, run)
- Container lifecycle management (start, stop, restart, remove)
- Automated deployment pipelines and orchestration
- Port detection and intelligent container configuration
- Registry authentication and image management
"""

# Core models
from .models import (
    DeployRequest,
    DockerfileInfo,
    ContainerInfo,
    ImageInfo,
    BuildContext,
    ContainerRunOptions,
    DockerRegistryCredentials,
    PortDetectionResult
)

# Engine operations
from .engine import (
    docker_login,
    docker_logout,
    build_image,
    push_image,
    pull_image,
    list_images,
    remove_image,
    run_container,
    list_containers,
    stop_container,
    start_container,
    restart_container,
    remove_container,
    get_container_logs,
    inspect_container
)

# Deployment services
from .services import (
    deploy_application,
    deploy_and_run_container,
    create_deployment_plan,
    scale_application
)

# Utilities
from .utils import (
    detect_project_ports,
    parse_dockerfile_info,
    detect_project_type,
    generate_container_name
)

__all__ = [
    # Models
    "DeployRequest",
    "DockerfileInfo",
    "ContainerInfo",
    "ImageInfo",
    "BuildContext",
    "ContainerRunOptions",
    "DockerRegistryCredentials",
    "PortDetectionResult",
    
    # Engine operations
    "docker_login",
    "docker_logout",
    "build_image",
    "push_image",
    "pull_image",
    "list_images",
    "remove_image",
    "run_container",
    "list_containers",
    "stop_container",
    "start_container",
    "restart_container",
    "remove_container",
    "get_container_logs",
    "inspect_container",
    
    # Deployment services
    "deploy_application",
    "deploy_and_run_container",
    "create_deployment_plan",
    "scale_application",
    
    # Utilities
    "detect_project_ports",
    "parse_dockerfile_info",
    "detect_project_type",
    "generate_container_name"
]

__version__ = "1.0.0"
__author__ = "Azure MCP DevOps Agent"
__description__ = "Modular Docker container management package"
