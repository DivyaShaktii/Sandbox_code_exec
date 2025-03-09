import os
import shutil
import asyncio
from datetime import datetime, timedelta
from .job_service import job_status, delete_job

async def cleanup_old_jobs():
    """Periodically clean up old jobs"""
    while True:
        try:
            cutoff_time = datetime.now() - timedelta(days=1)
            jobs_to_delete = []
            
            for job_id, job in job_status.items():
                job_time = datetime.fromisoformat(job['timestamp'])
                if job_time < cutoff_time:
                    jobs_to_delete.append(job_id)
            
            for job_id in jobs_to_delete:
                try:
                    if 'file_path' in job_status[job_id] and os.path.exists(job_status[job_id]['file_path']):
                        os.remove(job_status[job_id]['file_path'])
                    
                    if 'code_path' in job_status[job_id] and os.path.exists(job_status[job_id]['code_path']):
                        os.remove(job_status[job_id]['code_path'])
                    
                    if 'result_path' in job_status[job_id] and os.path.exists(job_status[job_id]['result_path']):
                        shutil.rmtree(job_status[job_id]['result_path'])
                    
                    delete_job(job_id)
                except:
                    pass
                    
            # Sleep for 1 hour before next cleanup
            await asyncio.sleep(3600)
        except:
            # If cleanup fails, try again later
            await asyncio.sleep(3600)

async def cleanup_job_files(job_id: str):
    """Clean up files associated with a job"""
    if job_id not in job_status:
        return False
    
    try:
        if 'file_path' in job_status[job_id] and os.path.exists(job_status[job_id]['file_path']):
            os.remove(job_status[job_id]['file_path'])
        
        if 'code_path' in job_status[job_id] and os.path.exists(job_status[job_id]['code_path']):
            os.remove(job_status[job_id]['code_path'])
        
        if 'result_path' in job_status[job_id] and os.path.exists(job_status[job_id]['result_path']):
            shutil.rmtree(job_status[job_id]['result_path'])
        
        return True
    except Exception as e:
        print(f"Error cleaning up job {job_id}: {str(e)}")
        return False 