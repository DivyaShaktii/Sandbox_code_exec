import os
import asyncio
import subprocess
from typing import Dict, Any
from .job_service import update_job_status

async def execute_code_in_sandbox(job_id: str, file_path: str, code_path: str, result_path: str, max_execution_time: int):
    """
    Execute Python code in a restricted sandbox environment using Docker.
    """
    try:
        update_job_status(job_id, 'running')
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Converting Windows path to Docker-compatible path
        if os.name == 'nt':  # Checking for windows
            file_path = file_path.replace('\\', '/').replace('C:', '/c')
            code_path = code_path.replace('\\', '/').replace('C:', '/c')
            result_path = result_path.replace('\\', '/').replace('C:', '/c')
        
        docker_cmd = [
            'docker', 'run', '--rm',
            #  resource limits
            '--memory=512m', '--cpu-shares=512',
            # timeout
            '--stop-timeout', str(max_execution_time),
            # Mount volumes for file access
            '-v', f"{file_path}:/data/input_file{file_ext}:ro",
            '-v', f"{code_path}:/data/process.py:ro",
            '-v', f"{result_path}:/data/output:rw",
            # Use minimal Python image
            'python-sandbox',
            # Run with restricted permissions
            'sh', '-c', "cd /data && python -m process"
        ]
        
        # command for debugging
        print(f"Executing Docker command: {' '.join(docker_cmd)}")
        update_job_status(job_id, 'running', docker_cmd=' '.join(docker_cmd))
        
        # regular subprocess on Windows instead of asyncio.create_subprocess_exec
        if os.name == 'nt':
            await _execute_windows(job_id, docker_cmd, max_execution_time)
        else:
            # Using asyncio on non-Windows platforms
            await _execute_unix(job_id, docker_cmd, max_execution_time)
            
    except Exception as e:
        import traceback
        update_job_status(
            job_id, 
            'failed', 
            error=f"Exception: {str(e)}\n{traceback.format_exc()}"
        )

async def _execute_windows(job_id: str, docker_cmd: list, max_execution_time: int):
    """Execute code in sandbox on Windows systems"""
    process = subprocess.Popen(
        docker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )
    
    try:
        stdout, stderr = process.communicate(timeout=max_execution_time)
        
        exit_code = process.returncode
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        update_job_status(job_id, 'running', stdout=stdout_text, stderr=stderr_text)
        
        if exit_code != 0:
            update_job_status(
                job_id, 
                'failed', 
                error=f"Exit code: {exit_code}\nStderr: {stderr_text}"
            )
        else:
            update_job_status(job_id, 'completed')
            
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        update_job_status(
            job_id, 
            'timeout', 
            error=f"Execution timed out after {max_execution_time} seconds"
        )

async def _execute_unix(job_id: str, docker_cmd: list, max_execution_time: int):
    """Execute code in sandbox on Unix-like systems"""
    process = await asyncio.create_subprocess_exec(
        *docker_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=max_execution_time
        )
        
        exit_code = process.returncode
        stdout_text = stdout.decode('utf-8')
        stderr_text = stderr.decode('utf-8')
        
        update_job_status(job_id, 'running', stdout=stdout_text, stderr=stderr_text)
        
        if exit_code != 0:
            update_job_status(
                job_id, 
                'failed', 
                error=f"Exit code: {exit_code}\nStderr: {stderr_text}"
            )
        else:
            update_job_status(job_id, 'completed')
            
    except asyncio.TimeoutError:
        # Killing the process if it times out
        if process.returncode is None:
            process.kill()
            
        update_job_status(
            job_id, 
            'timeout', 
            error=f"Execution timed out after {max_execution_time} seconds"
        )

def get_code_template():
    """Return a template for processing files"""
    return """
# This is a template for processing your data file
# The input file is available as "input_file.csv" (or .xlsx/.xls)
# You should output your results to the current directory

import pandas as pd
import json

# Determine file type and read accordingly
import os
df = pd.read_csv('/data/input_file.csv')

# Process your data here
# Example: Calculate summary statistics
result = {
    'row_count': len(df),
    'column_count': len(df.columns),
    'columns': list(df.columns),
    'summary': df.describe().to_dict()
}
print("result", result)
df.columns = [col.upper() for col in df.columns]

# Save results

#  Save as CSV
df.to_csv('/data/output/processed_data.csv', index=False)


print("Processing completed successfully")
"""