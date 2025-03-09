import os
import uuid
from datetime import datetime
from typing import Dict, Any

# Job status tracking
job_status: Dict[str, Dict[str, Any]] = {}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def create_job(filename: str, file_path: str) -> str:
    """Create a new job and return its ID"""
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        'id': job_id,
        'filename': filename,
        'status': 'uploaded',
        'timestamp': datetime.now().isoformat(),
        'file_path': file_path
    }
    
    return job_id

def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status with additional information"""
    if job_id in job_status:
        job_status[job_id]['status'] = status
        for key, value in kwargs.items():
            job_status[job_id][key] = value

def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the current status of a job"""
    return job_status.get(job_id, {})

def delete_job(job_id: str):
    """Delete a job from the status tracking"""
    if job_id in job_status:
        del job_status[job_id]