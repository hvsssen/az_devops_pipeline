"""
Helm Charts Service for Kubernetes Deployments
Handles Helm chart generation and deployment to AKS
"""
import subprocess
import yaml
import os
from typing import Dict, List, Optional
from pathlib import Path

# Import Azure CLI command from the Azure CLI client
from ..cli.client import AZ_CMD


class HelmService:
    """Helm charts management service"""
    
    def __init__(self, base_path: str = None):
        if base_path:
            # Use the base_path directly as the charts directory instead of adding helm-charts
            self.charts_dir = base_path
        else:
            self.charts_dir = "./helm-charts"
        
    async def create_helm_chart(self, chart_name: str, app_name: str, image_repository: str, 
                               image_tag: str = "latest", port: int = 80, 
                               namespace: str = "default") -> Dict:
        """Create a Helm chart for application deployment"""
        try:
            chart_path = os.path.join(self.charts_dir, chart_name)
            
            # Create chart directory structure
            os.makedirs(chart_path, exist_ok=True)
            os.makedirs(os.path.join(chart_path, "templates"), exist_ok=True)
            
            # Chart.yaml
            chart_yaml = {
                "apiVersion": "v2",
                "name": chart_name,
                "description": f"A Helm chart for {app_name}",
                "version": "0.1.0",
                "appVersion": "1.0.0"
            }
            
            with open(os.path.join(chart_path, "Chart.yaml"), "w") as f:
                yaml.dump(chart_yaml, f, default_flow_style=False)
            
            # values.yaml
            values_yaml = {
                "replicaCount": 1,
                "image": {
                    "repository": image_repository,
                    "tag": image_tag,
                    "pullPolicy": "IfNotPresent"
                },
                "service": {
                    "type": "LoadBalancer",
                    "port": 80,
                    "targetPort": port
                },
                "ingress": {
                    "enabled": False,
                    "className": "",
                    "annotations": {},
                    "hosts": [
                        {
                            "host": f"{app_name}.local",
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix"
                                }
                            ]
                        }
                    ]
                },
                "resources": {
                    "limits": {
                        "cpu": "500m",
                        "memory": "512Mi"
                    },
                    "requests": {
                        "cpu": "250m", 
                        "memory": "256Mi"
                    }
                },
                "autoscaling": {
                    "enabled": False,
                    "minReplicas": 1,
                    "maxReplicas": 10,
                    "targetCPUUtilizationPercentage": 80
                },
                "nodeSelector": {},
                "tolerations": [],
                "affinity": {}
            }
            
            with open(os.path.join(chart_path, "values.yaml"), "w") as f:
                yaml.dump(values_yaml, f, default_flow_style=False)
            
            # Deployment template
            deployment_template = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{chart_name}.fullname" . }}}}
  labels:
    {{{{- include "{chart_name}.labels" . | nindent 4 }}}}
spec:
  {{{{- if not .Values.autoscaling.enabled }}}}
  replicas: {{{{ .Values.replicaCount }}}}
  {{{{- end }}}}
  selector:
    matchLabels:
      {{{{- include "{chart_name}.selectorLabels" . | nindent 6 }}}}
  template:
    metadata:
      labels:
        {{{{- include "{chart_name}.selectorLabels" . | nindent 8 }}}}
    spec:
      containers:
        - name: {{{{ .Chart.Name }}}}
          image: "{{{{ .Values.image.repository }}}}:{{{{ .Values.image.tag }}}}"
          imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
          ports:
            - name: http
              containerPort: {port}
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            {{{{- toYaml .Values.resources | nindent 12 }}}}
"""
            
            with open(os.path.join(chart_path, "templates", "deployment.yaml"), "w") as f:
                f.write(deployment_template)
            
            # Service template
            service_template = f"""apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{chart_name}.fullname" . }}}}
  labels:
    {{{{- include "{chart_name}.labels" . | nindent 4 }}}}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
    - port: {{{{ .Values.service.port }}}}
      targetPort: {{{{ .Values.service.targetPort }}}}
      protocol: TCP
      name: http
  selector:
    {{{{- include "{chart_name}.selectorLabels" . | nindent 4 }}}}
"""
            
            with open(os.path.join(chart_path, "templates", "service.yaml"), "w") as f:
                f.write(service_template)
            
            # Helpers template
            helpers_template = f"""{{{{/*
Expand the name of the chart.
*/}}}}
{{{{- define "{chart_name}.name" -}}}}
{{{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}

{{{{/*
Create a default fully qualified app name.
*/}}}}
{{{{- define "{chart_name}.fullname" -}}}}
{{{{- if .Values.fullnameOverride }}}}
{{{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}}}
{{{{- else }}}}
{{{{- $name := default .Chart.Name .Values.nameOverride }}}}
{{{{- if contains $name .Release.Name }}}}
{{{{- .Release.Name | trunc 63 | trimSuffix "-" }}}}
{{{{- else }}}}
{{{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}
{{{{- end }}}}
{{{{- end }}}}

{{{{/*
Create chart name and version as used by the chart label.
*/}}}}
{{{{- define "{chart_name}.chart" -}}}}
{{{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}

{{{{/*
Common labels
*/}}}}
{{{{- define "{chart_name}.labels" -}}}}
helm.sh/chart: {{{{ include "{chart_name}.chart" . }}}}
{{{{ include "{chart_name}.selectorLabels" . }}}}
{{{{- if .Chart.AppVersion }}}}
app.kubernetes.io/version: {{{{ .Chart.AppVersion | quote }}}}
{{{{- end }}}}
app.kubernetes.io/managed-by: {{{{ .Release.Service }}}}
{{{{- end }}}}

{{{{/*
Selector labels
*/}}}}
{{{{- define "{chart_name}.selectorLabels" -}}}}
app.kubernetes.io/name: {{{{ include "{chart_name}.name" . }}}}
app.kubernetes.io/instance: {{{{ .Release.Name }}}}
{{{{- end }}}}
"""
            
            with open(os.path.join(chart_path, "templates", "_helpers.tpl"), "w") as f:
                f.write(helpers_template)
            
            return {
                "status": "success",
                "chart_name": chart_name,
                "chart_path": chart_path,
                "app_name": app_name,
                "image_repository": image_repository,
                "message": f"Helm chart {chart_name} created successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create Helm chart: {str(e)}"
            }
    
    async def install_helm_chart(self, chart_name: str, release_name: str, 
                                namespace: str = "default", values_override: Dict = None) -> Dict:
        """Install Helm chart to Kubernetes cluster"""
        try:
            chart_path = os.path.join(self.charts_dir, chart_name)
            
            if not os.path.exists(chart_path):
                return {
                    "status": "error",
                    "message": f"Chart {chart_name} not found at {chart_path}"
                }
            
            # First, get AKS credentials to ensure kubectl points to the right cluster
            try:
                # Use the full Azure CLI path
                az_cmd = r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
                creds_cmd = [
                    az_cmd, "aks", "get-credentials", 
                    "--resource-group", "rg-mcp-devops",
                    "--name", "aks-mcp-devops-new",
                    "--overwrite-existing"
                ]
                creds_result = subprocess.run(creds_cmd, capture_output=True, text=True, timeout=60)
                if creds_result.returncode != 0:
                    return {
                        "status": "error",
                        "message": f"Failed to get AKS credentials: {creds_result.stderr}"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Exception getting AKS credentials: {str(e)}"
                }
            
            # Create namespace if it doesn't exist
            namespace_cmd = ["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"]
            subprocess.run(namespace_cmd, capture_output=True)
            
            # Apply namespace
            apply_namespace = ["kubectl", "apply", "-f", "-"]
            result = subprocess.run(apply_namespace, input=subprocess.run(namespace_cmd, capture_output=True, text=True).stdout, text=True)
            
            # Build helm install command
            cmd = [
                "helm", "install", release_name, chart_path,
                "--namespace", namespace,
                "--create-namespace"
            ]
            
            # Add custom values if provided
            if values_override:
                values_file = os.path.join(chart_path, "custom-values.yaml")
                with open(values_file, "w") as f:
                    yaml.dump(values_override, f, default_flow_style=False)
                cmd.extend(["--values", values_file])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "release_name": release_name,
                    "chart_name": chart_name,
                    "namespace": namespace,
                    "message": f"Helm chart {chart_name} installed as {release_name}",
                    "output": result.stdout
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to install Helm chart: {result.stderr}",
                    "output": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception installing Helm chart: {str(e)}"
            }
    
    async def upgrade_helm_release(self, release_name: str, chart_name: str, 
                                  namespace: str = "default", values_override: Dict = None) -> Dict:
        """Upgrade existing Helm release"""
        try:
            chart_path = os.path.join(self.charts_dir, chart_name)
            
            cmd = [
                "helm", "upgrade", release_name, chart_path,
                "--namespace", namespace
            ]
            
            if values_override:
                values_file = os.path.join(chart_path, "upgrade-values.yaml")
                with open(values_file, "w") as f:
                    yaml.dump(values_override, f, default_flow_style=False)
                cmd.extend(["--values", values_file])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "release_name": release_name,
                    "message": f"Helm release {release_name} upgraded successfully",
                    "output": result.stdout
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to upgrade Helm release: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Exception upgrading Helm release: {str(e)}"
            }
    
    async def uninstall_helm_release(self, release_name: str, namespace: str = "default") -> Dict:
        """Uninstall Helm release"""
        try:
            cmd = ["helm", "uninstall", release_name, "--namespace", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "release_name": release_name,
                    "message": f"Helm release {release_name} uninstalled successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to uninstall Helm release: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception uninstalling Helm release: {str(e)}"
            }
    
    async def list_helm_releases(self, namespace: str = "default") -> Dict:
        """List Helm releases in namespace"""
        try:
            cmd = ["helm", "list", "--namespace", namespace, "--output", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                releases = yaml.safe_load(result.stdout) if result.stdout.strip() else []
                return {
                    "status": "success",
                    "namespace": namespace,
                    "releases": releases,
                    "count": len(releases)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to list Helm releases: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception listing Helm releases: {str(e)}"
            }
