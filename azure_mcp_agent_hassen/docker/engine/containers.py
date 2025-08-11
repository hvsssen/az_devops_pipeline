"""
Docker Container Management

Container lifecycle operations including creation, running, 
stopping, and monitoring of Docker containers.
"""

import subprocess
import logging
from typing import Dict, List, Optional, Any

from ..models import ContainerInfo, ContainerRunOptions


def run_container(options: ContainerRunOptions) -> Dict[str, Any]:
    """Run a Docker container with specified options"""
    try:
        cmd = ["docker", "run"]
        
        # Add detach flag
        if options.detach:
            cmd.append("-d")
        
        # Add remove flag
        if options.remove:
            cmd.append("--rm")
        
        # Add container name
        if options.name:
            cmd.extend(["--name", options.name])
        
        # Add port mappings
        for host_port, container_port in options.ports.items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])
        
        # Add environment variables
        for key, value in options.environment.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # Add volume mappings
        for host_path, container_path in options.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        # Add network
        if options.network:
            cmd.extend(["--network", options.network])
        
        # Add restart policy
        if options.restart_policy:
            cmd.extend(["--restart", options.restart_policy])
        
        # Add image
        cmd.append(options.image)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        
        return {
            "status": "ok",
            "container_id": container_id,
            "message": f"Container started successfully",
            "image": options.image,
            "name": options.name
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run container: {e.stderr}")
        return {"status": "error", "error": f"Failed to run container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Run container error: {e}")
        return {"status": "error", "error": str(e)}


def list_containers(all_containers: bool = False) -> Dict[str, Any]:
    """List Docker containers"""
    try:
        cmd = ["docker", "ps", "--format", 
               "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Command}}"]
        
        if all_containers:
            cmd.append("-a")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        containers = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 6:
                    containers.append(ContainerInfo(
                        container_id=parts[0],
                        name=parts[1],
                        image=parts[2],
                        status=parts[3],
                        ports=[parts[4]] if parts[4] else [],
                        created=parts[5],
                        command=parts[6] if len(parts) > 6 else None
                    ))
        
        return {
            "status": "ok",
            "containers": [container.dict() for container in containers],
            "count": len(containers)
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to list containers: {e.stderr}")
        return {"status": "error", "error": f"Failed to list containers: {e.stderr}"}
    except Exception as e:
        logging.error(f"List containers error: {e}")
        return {"status": "error", "error": str(e)}


def stop_container(container_id: str, timeout: int = 10) -> Dict[str, Any]:
    """Stop a running Docker container"""
    try:
        result = subprocess.run(
            ["docker", "stop", "-t", str(timeout), container_id],
            capture_output=True, text=True, check=True
        )
        
        return {
            "status": "ok",
            "container_id": container_id,
            "message": f"Container {container_id} stopped successfully"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to stop container: {e.stderr}")
        return {"status": "error", "error": f"Failed to stop container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Stop container error: {e}")
        return {"status": "error", "error": str(e)}


def start_container(container_id: str) -> Dict[str, Any]:
    """Start a stopped Docker container"""
    try:
        result = subprocess.run(
            ["docker", "start", container_id],
            capture_output=True, text=True, check=True
        )
        
        return {
            "status": "ok",
            "container_id": container_id,
            "message": f"Container {container_id} started successfully"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to start container: {e.stderr}")
        return {"status": "error", "error": f"Failed to start container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Start container error: {e}")
        return {"status": "error", "error": str(e)}


def restart_container(container_id: str, timeout: int = 10) -> Dict[str, Any]:
    """Restart a Docker container"""
    try:
        result = subprocess.run(
            ["docker", "restart", "-t", str(timeout), container_id],
            capture_output=True, text=True, check=True
        )
        
        return {
            "status": "ok",
            "container_id": container_id,
            "message": f"Container {container_id} restarted successfully"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to restart container: {e.stderr}")
        return {"status": "error", "error": f"Failed to restart container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Restart container error: {e}")
        return {"status": "error", "error": str(e)}


def remove_container(container_id: str, force: bool = False) -> Dict[str, Any]:
    """Remove a Docker container"""
    try:
        cmd = ["docker", "rm"]
        
        if force:
            cmd.append("-f")
        
        cmd.append(container_id)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "container_id": container_id,
            "message": f"Container {container_id} removed successfully"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to remove container: {e.stderr}")
        return {"status": "error", "error": f"Failed to remove container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Remove container error: {e}")
        return {"status": "error", "error": str(e)}


def get_container_logs(container_id: str, tail: int = 100, follow: bool = False) -> Dict[str, Any]:
    """Get logs from a Docker container"""
    try:
        cmd = ["docker", "logs"]
        
        if tail > 0:
            cmd.extend(["--tail", str(tail)])
        
        if follow:
            cmd.append("-f")
        
        cmd.append(container_id)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "container_id": container_id,
            "logs": result.stdout,
            "errors": result.stderr
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get container logs: {e.stderr}")
        return {"status": "error", "error": f"Failed to get container logs: {e.stderr}"}
    except Exception as e:
        logging.error(f"Get container logs error: {e}")
        return {"status": "error", "error": str(e)}


def inspect_container(container_id: str) -> Dict[str, Any]:
    """Get detailed information about a Docker container"""
    try:
        result = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True, text=True, check=True
        )
        
        import json
        container_details = json.loads(result.stdout)[0]
        
        return {
            "status": "ok",
            "container_id": container_id,
            "details": container_details
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to inspect container: {e.stderr}")
        return {"status": "error", "error": f"Failed to inspect container: {e.stderr}"}
    except Exception as e:
        logging.error(f"Inspect container error: {e}")
        return {"status": "error", "error": str(e)}
