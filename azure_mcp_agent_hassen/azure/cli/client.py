"""
Azure CLI Interface

Core Azure CLI command execution and session management.
"""

import os
import subprocess
import asyncio
import json
import platform
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Azure CLI command based on platform
if platform.system() == "Windows":
    AZ_CMD = r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
else:
    AZ_CMD = "az"

STORAGE_FILE = Path("azure_auth_data.json")


def az_command(*args) -> Dict[str, Any]:
    """Execute Azure CLI command and return JSON output"""
    env = os.environ.copy()
    result = subprocess.run(
        [AZ_CMD, *args, "--output", "json"],
        capture_output=True,
        text=True,
        env=env
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {str(e)}, stdout: {result.stdout}")
        raise RuntimeError(f"Failed to parse JSON output: {str(e)}, stdout: {result.stdout}")


async def az_command_async(cmd: str) -> str:
    """Execute Azure CLI command asynchronously"""
    args = [AZ_CMD] + cmd.split()
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        return f"❌ Error: {stderr.decode()}"

    return stdout.decode()


def save_azure_session(subscriptions: List[Dict]) -> None:
    """Save Azure session data to file"""
    STORAGE_FILE.write_text(json.dumps(subscriptions, indent=2))
    logging.debug("Azure session saved to file")


def load_azure_session() -> Optional[List[Dict]]:
    """Load Azure session data from file"""
    if STORAGE_FILE.exists():
        return json.loads(STORAGE_FILE.read_text())
    return None


def ensure_cost_extension_installed() -> None:
    """Ensure Azure Cost Management extension is installed"""
    try:
        az_command("extension", "add", "--name", "costmanagement")
        logging.debug("costmanagement extension installed.")
    except RuntimeError as e:
        if "already installed" in str(e):
            logging.debug("costmanagement extension already installed.")
        else:
            logging.error(f"Failed to install costmanagement extension: {e}")


def check_azure_cli_available() -> bool:
    """Check if Azure CLI is available and working"""
    try:
        result = subprocess.run([AZ_CMD, "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def check_azure_login_status() -> bool:
    """Check if user is logged into Azure CLI"""
    try:
        az_command("account", "show")
        return True
    except RuntimeError:
        return False
