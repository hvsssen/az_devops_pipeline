import os
import subprocess
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # Loads .env if it exists

class DeployRequest(BaseModel):
    repo_full_name: str
    tag: str
    image_name: str
    repo_path: str



def docker_login():
    username = os.getenv("DOCKER_USERNAME")
    password = os.getenv("DOCKER_PASSWORD")

    if not username or not password:
        raise ValueError("DOCKER_USERNAME or DOCKER_PASSWORD not set in environment variables.")

    subprocess.run([
        "docker", "login",
        "--username", username,
        "--password", password
    ], check=True)
    print("✅ Docker login successful.")

def build_image(repo_path: str, image_name: str, tag: str = "latest"):
    # Ensure image name includes Docker Hub username if not already present
    if "/" not in image_name:
        username = os.getenv("DOCKER_USERNAME")
        if username:
            image_name = f"{username}/{image_name}"
    
    full_image_name = f"{image_name}:{tag}"
    subprocess.run(["docker", "build", "-t", full_image_name, repo_path], check=True)
    print(f"✅ Built Docker image: {full_image_name}")
    return full_image_name

def push_image(image_name: str, tag: str = "latest"):
    # Ensure image name includes Docker Hub username if not already present
    if "/" not in image_name:
        username = os.getenv("DOCKER_USERNAME")
        if username:
            image_name = f"{username}/{image_name}"
    
    full_image_name = f"{image_name}:{tag}"
    subprocess.run(["docker", "push", full_image_name], check=True)
    print(f"✅ Pushed Docker image: {full_image_name}")



def parse_dockerfile_ports(dockerfile_path: str) -> List[int]:
    """Extract EXPOSE ports from Dockerfile"""
    ports = []
    try:
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Find all EXPOSE instructions (case insensitive)
        expose_pattern = r'^EXPOSE\s+(.+)$'
        matches = re.findall(expose_pattern, content, re.MULTILINE | re.IGNORECASE)
        
        for match in matches:
            # Handle multiple ports in single EXPOSE line
            port_strings = match.split()
            for port_str in port_strings:
                # Extract numeric port (ignore protocol like 80/tcp)
                port_match = re.match(r'(\d+)', port_str.strip())
                if port_match:
                    ports.append(int(port_match.group(1)))
    
    except FileNotFoundError:
        print(f"⚠️ Dockerfile not found at {dockerfile_path}")
    except Exception as e:
        print(f"⚠️ Error parsing Dockerfile: {e}")
    
    return ports

def detect_application_ports(repo_path: str) -> Dict[str, List[int]]:
    """Detect ports from various sources in the repository"""
    detected_ports = {
        "dockerfile": [],
        "package_json": [],
        "default_suggestions": []
    }
    
    # Check Dockerfile
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    detected_ports["dockerfile"] = parse_dockerfile_ports(dockerfile_path)
    
    # Check package.json for Node.js apps
    package_json_path = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json_path):
        try:
            import json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Look for common port patterns in scripts
            scripts = package_data.get("scripts", {})
            for script in scripts.values():
                if isinstance(script, str):
                    # Look for port patterns like --port 3000, -p 8080, etc.
                    port_matches = re.findall(r'(?:--port|-p|PORT=)[\s=](\d+)', script)
                    detected_ports["package_json"].extend([int(p) for p in port_matches])
        except Exception as e:
            print(f"⚠️ Error parsing package.json: {e}")
    
    # Suggest default ports based on project type
    if os.path.exists(package_json_path):
        detected_ports["default_suggestions"] = [3000, 8000, 8080]  # Node.js common ports
    elif os.path.exists(os.path.join(repo_path, "requirements.txt")) or os.path.exists(os.path.join(repo_path, "manage.py")):
        detected_ports["default_suggestions"] = [8000, 5000, 8080]  # Python/Django common ports
    elif os.path.exists(os.path.join(repo_path, "pom.xml")) or os.path.exists(os.path.join(repo_path, "build.gradle")):
        detected_ports["default_suggestions"] = [8080, 8090, 9090]  # Java common ports
    else:
        detected_ports["default_suggestions"] = [80, 8000, 8080]  # Generic web apps
    
    return detected_ports

def get_recommended_ports(repo_path: str) -> List[int]:
    """Get recommended ports for a repository with priority order"""
    port_info = detect_application_ports(repo_path)
    
    # Priority: Dockerfile > package.json > defaults
    if port_info["dockerfile"]:
        return port_info["dockerfile"]
    elif port_info["package_json"]:
        return port_info["package_json"]
    else:
        return port_info["default_suggestions"][:1]  # Return just the first default

def run_container(image_name: str, tag: str = "latest", container_name: str = None, ports: dict = None, detach: bool = True, repo_path: str = None):
    # Ensure image name includes Docker Hub username if not already present
    if "/" not in image_name:
        username = os.getenv("DOCKER_USERNAME")
        if username:
            image_name = f"{username}/{image_name}"

    full_image_name = f"{image_name}:{tag}"

    cmd = ["docker", "run"]

    if detach:
        cmd.append("-d")

    if container_name:
        cmd += ["--name", container_name]

    # Auto-detect ports if not provided and repo_path is available
    if ports is None and repo_path:
        recommended_ports = get_recommended_ports(repo_path)
        if recommended_ports:
            ports = {}
            for port in recommended_ports:
                ports[port] = port  # Map container port to same host port
            print(f"🔍 Auto-detected ports: {recommended_ports}")

    # Use default port if nothing detected
    if ports is None:
        ports = {8000: 8000}
        print("⚠️ No ports detected, using default 8000:8000")

    if ports:
        for host_port, container_port in ports.items():
            cmd += ["-p", f"{host_port}:{container_port}"]

    cmd.append(full_image_name)

    subprocess.run(cmd, check=True)
    print(f"✅ Running container from image: {full_image_name}")
    print(f"🌐 Accessible on ports: {list(ports.keys())}")

def run_container_with_auto_ports(image_name: str, repo_path: str, tag: str = "latest", container_name: str = None):
    """Enhanced run_container that automatically detects ports from repository"""
    port_info = detect_application_ports(repo_path)
    recommended_ports = get_recommended_ports(repo_path)
    
    # Create port mapping
    ports = {}
    for port in recommended_ports:
        ports[port] = port
    
    print(f"📊 Port Detection Summary:")
    print(f"  Dockerfile ports: {port_info['dockerfile']}")
    print(f"  Package.json ports: {port_info['package_json']}")
    print(f"  Default suggestions: {port_info['default_suggestions']}")
    print(f"  Using ports: {recommended_ports}")
    
    return run_container(
        image_name=image_name,
        tag=tag,
        container_name=container_name,
        ports=ports,
        repo_path=repo_path
    )
