"""
Docker Utilities Package

Common utilities and helpers for Docker operations including
port detection, project analysis, and container configuration.
"""

from .ports import (
    detect_project_ports,
    parse_dockerfile_info,
    detect_nodejs_ports,
    detect_python_ports,
    detect_framework_ports,
    detect_env_ports,
    detect_project_type,
    get_default_ports_for_type,
    generate_container_name
)

__all__ = [
    "detect_project_ports",
    "parse_dockerfile_info",
    "detect_nodejs_ports",
    "detect_python_ports",
    "detect_framework_ports",
    "detect_env_ports",
    "detect_project_type",
    "get_default_ports_for_type",
    "generate_container_name"
]
