"""
Docker Port Detection and Configuration Utilities

Utilities for detecting ports from project configuration and
intelligently configuring container deployments.
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional, Any

from ..models import PortDetectionResult, DockerfileInfo


def detect_project_ports(repo_path: str) -> PortDetectionResult:
    """Detect ports from various project sources"""
    try:
        detected_ports = []
        dockerfile_ports = []
        recommended_ports = []
        config_ports = []
        default_ports = []
        
        # Check Dockerfile for EXPOSE directives
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        if os.path.exists(dockerfile_path):
            dockerfile_info = parse_dockerfile_info(dockerfile_path)
            dockerfile_ports = dockerfile_info.exposed_ports
            detected_ports.extend(dockerfile_ports)
        
        # Check package.json for Node.js projects
        package_json_path = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json_path):
            config_ports.extend(detect_nodejs_ports(package_json_path))
        
        # Check Python configuration files
        config_ports.extend(detect_python_ports(repo_path))
        
        # Check for common framework configurations
        framework_ports = detect_framework_ports(repo_path)
        default_ports.extend(framework_ports)
        
        # Check for environment files
        env_ports = detect_env_ports(repo_path)
        config_ports.extend(env_ports)
        
        # Combine all detected ports
        all_ports = set(detected_ports + config_ports + default_ports)
        detected_ports = sorted(list(all_ports))
        
        # Generate recommendations based on project type
        if not detected_ports:
            project_type = detect_project_type(repo_path)
            recommended_ports = get_default_ports_for_type(project_type)
        
        return PortDetectionResult(
            detected_ports=detected_ports,
            dockerfile_ports=dockerfile_ports,
            recommended_ports=recommended_ports,
            config_ports=config_ports,
            default_ports=default_ports
        )
        
    except Exception as e:
        logging.error(f"Port detection failed: {e}")
        return PortDetectionResult()


def parse_dockerfile_info(dockerfile_path: str) -> DockerfileInfo:
    """Parse Dockerfile to extract configuration information"""
    info = DockerfileInfo()
    
    try:
        with open(dockerfile_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.upper().startswith("FROM"):
                    info.base_image = line.split()[1]
                elif line.upper().startswith("EXPOSE"):
                    ports = re.findall(r'\d+', line)
                    info.exposed_ports.extend(int(p) for p in ports)
                elif line.upper().startswith("ENV"):
                    parts = line.split(None, 2)
                    if len(parts) >= 3:
                        info.env_vars[parts[1]] = parts[2]
                elif line.upper().startswith("ARG"):
                    info.build_args.append(line.split()[1])
                elif line.upper().startswith("LABEL"):
                    label_matches = re.findall(r'(\w+)="([^"]+)"', line)
                    for k, v in label_matches:
                        info.labels[k] = v
                elif line.upper().startswith("WORKDIR"):
                    info.working_dir = line.split()[1]
                elif line.upper().startswith("ENTRYPOINT"):
                    info.entrypoint = parse_docker_command(line[10:].strip())
                elif line.upper().startswith("CMD"):
                    info.cmd = parse_docker_command(line[3:].strip())
                    
    except FileNotFoundError:
        logging.warning(f"Dockerfile not found at {dockerfile_path}")
    except Exception as e:
        logging.error(f"Failed to parse Dockerfile: {e}")
        
    return info


def detect_nodejs_ports(package_json_path: str) -> List[int]:
    """Detect ports from Node.js package.json"""
    ports = []
    
    try:
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        # Check scripts for port references
        scripts = package_data.get("scripts", {})
        for script in scripts.values():
            port_matches = re.findall(r'--port[=\s]+(\d+)', script)
            ports.extend(int(p) for p in port_matches)
            
            # Check for common port patterns
            if "3000" in script:
                ports.append(3000)
            elif "8000" in script:
                ports.append(8000)
            elif "5000" in script:
                ports.append(5000)
        
        # Check dependencies for framework defaults
        dependencies = {**package_data.get("dependencies", {}), 
                       **package_data.get("devDependencies", {})}
        
        if "express" in dependencies:
            ports.append(3000)
        elif "koa" in dependencies:
            ports.append(3000)
        elif "fastify" in dependencies:
            ports.append(3000)
        elif "next" in dependencies:
            ports.append(3000)
        elif "nuxt" in dependencies:
            ports.append(3000)
        elif "vue" in dependencies:
            ports.append(8080)
        elif "react" in dependencies:
            ports.append(3000)
        elif "angular" in dependencies:
            ports.append(4200)
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Failed to parse package.json: {e}")
    except Exception as e:
        logging.error(f"Error detecting Node.js ports: {e}")
        
    return list(set(ports))


def detect_python_ports(repo_path: str) -> List[int]:
    """Detect ports from Python project files"""
    ports = []
    
    # Check requirements.txt for framework hints
    requirements_path = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            with open(requirements_path, 'r') as f:
                requirements = f.read().lower()
                
            if "django" in requirements:
                ports.append(8000)
            elif "flask" in requirements:
                ports.append(5000)
            elif "fastapi" in requirements:
                ports.append(8000)
            elif "tornado" in requirements:
                ports.append(8888)
            elif "bottle" in requirements:
                ports.append(8080)
                
        except Exception as e:
            logging.error(f"Error reading requirements.txt: {e}")
    
    # Check Python files for port configurations
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Look for app.run(), uvicorn.run(), etc.
                    port_patterns = [
                        r'port[=\s]*(\d+)',
                        r'PORT[=\s]*(\d+)',
                        r'listen[=\s]*(\d+)',
                        r'bind[=\s]*["\'].*:(\d+)["\']'
                    ]
                    
                    for pattern in port_patterns:
                        matches = re.findall(pattern, content)
                        ports.extend(int(p) for p in matches)
                        
                except Exception as e:
                    logging.debug(f"Error reading {file_path}: {e}")
                    
    return list(set(ports))


def detect_framework_ports(repo_path: str) -> List[int]:
    """Detect framework-specific default ports"""
    ports = []
    
    # Check for specific framework files
    framework_files = {
        "next.config.js": [3000],
        "nuxt.config.js": [3000],
        "angular.json": [4200],
        "vue.config.js": [8080],
        "gatsby-config.js": [8000],
        "svelte.config.js": [5000],
        "manage.py": [8000],  # Django
        "app.py": [5000],     # Flask
        "main.py": [8000],    # FastAPI
    }
    
    for filename, default_ports in framework_files.items():
        if os.path.exists(os.path.join(repo_path, filename)):
            ports.extend(default_ports)
    
    return list(set(ports))


def detect_env_ports(repo_path: str) -> List[int]:
    """Detect ports from environment files"""
    ports = []
    
    env_files = [".env", ".env.local", ".env.development", ".env.production"]
    
    for env_file in env_files:
        env_path = os.path.join(repo_path, env_file)
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    content = f.read()
                
                # Look for PORT environment variables
                port_matches = re.findall(r'PORT[=\s]*(\d+)', content, re.IGNORECASE)
                ports.extend(int(p) for p in port_matches)
                
            except Exception as e:
                logging.error(f"Error reading {env_path}: {e}")
    
    return list(set(ports))


def detect_project_type(repo_path: str) -> str:
    """Detect the primary project type/framework"""
    
    # Check for specific files
    if os.path.exists(os.path.join(repo_path, "package.json")):
        return "node"
    elif os.path.exists(os.path.join(repo_path, "requirements.txt")) or \
         os.path.exists(os.path.join(repo_path, "pyproject.toml")):
        return "python"
    elif os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        return "rust"
    elif os.path.exists(os.path.join(repo_path, "go.mod")):
        return "go"
    elif os.path.exists(os.path.join(repo_path, "pom.xml")):
        return "java"
    elif os.path.exists(os.path.join(repo_path, "Gemfile")):
        return "ruby"
    elif os.path.exists(os.path.join(repo_path, "composer.json")):
        return "php"
    
    return "unknown"


def get_default_ports_for_type(project_type: str) -> List[int]:
    """Get default ports for project type"""
    defaults = {
        "node": [3000, 8000],
        "python": [5000, 8000],
        "rust": [8080],
        "go": [8080],
        "java": [8080, 8443],
        "ruby": [3000],
        "php": [80, 8080],
        "unknown": [8080]
    }
    
    return defaults.get(project_type, [8080])


def parse_docker_command(command_str: str) -> List[str]:
    """Parse Docker ENTRYPOINT/CMD string into list"""
    try:
        # Handle JSON format
        if command_str.strip().startswith('['):
            return json.loads(command_str)
        
        # Handle shell format - simple split for now
        return command_str.split()
        
    except Exception as e:
        logging.error(f"Failed to parse Docker command: {e}")
        return [command_str]


def generate_container_name(image_name: str, tag: str = "latest") -> str:
    """Generate a safe container name from image name and tag"""
    # Remove registry prefix if present
    if "/" in image_name:
        image_name = image_name.split("/")[-1]
    
    # Replace invalid characters
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', image_name)
    
    # Add tag if not latest
    if tag != "latest":
        safe_tag = re.sub(r'[^a-zA-Z0-9_.-]', '_', tag)
        safe_name = f"{safe_name}_{safe_tag}"
    
    return safe_name
