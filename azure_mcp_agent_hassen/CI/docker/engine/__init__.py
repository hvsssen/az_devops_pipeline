"""
Docker Engine Package

Core Docker engine operations including client authentication,
image management, and container lifecycle operations.
"""

from .client import (
    docker_login,
    docker_logout,
    build_image,
    push_image,
    pull_image,
    list_images,
    remove_image
)

from .containers import (
    run_container,
    list_containers,
    stop_container,
    start_container,
    restart_container,
    remove_container,
    get_container_logs,
    inspect_container
)

__all__ = [
    # Client operations
    "docker_login",
    "docker_logout",
    "build_image",
    "push_image",
    "pull_image",
    "list_images",
    "remove_image",
    
    # Container operations
    "run_container",
    "list_containers", 
    "stop_container",
    "start_container",
    "restart_container",
    "remove_container",
    "get_container_logs",
    "inspect_container"
]
