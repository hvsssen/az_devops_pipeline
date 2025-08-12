from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class WorkflowJob(BaseModel):
    name: str
    runs_on: str = "ubuntu-latest"
    steps: List[dict]

class WorkflowConfig(BaseModel):
    name: str
    on: dict
    jobs: dict


