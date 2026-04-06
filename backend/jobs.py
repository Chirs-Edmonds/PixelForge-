"""
jobs.py — In-memory job state store for PixelForge background tasks.

Each job has the shape:
    {
        "status":       "pending" | "running" | "done" | "error",
        "step":         str,        # e.g. "blender", "assemble", "tripo3d"
        "progress_msg": str,        # human-readable progress message
        "error":        str | None, # error message if status == "error"
        "output":       str | None, # relative output path when done
    }
"""

from typing import Dict, Any

jobs: Dict[str, Dict[str, Any]] = {}


def create_job(job_id: str) -> None:
    jobs[job_id] = {
        "status":       "pending",
        "step":         "",
        "progress_msg": "Queued...",
        "error":        None,
        "output":       None,
    }


def update_job(job_id: str, **kwargs) -> None:
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def get_job(job_id: str) -> Dict[str, Any] | None:
    return jobs.get(job_id)
