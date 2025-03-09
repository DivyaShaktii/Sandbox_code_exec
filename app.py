import os
import json
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Response
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import uvicorn

# Import modules
from config import (
    UPLOAD_FOLDER, CODE_FOLDER, RESULTS_FOLDER, 
    ALLOWED_EXTENSIONS, MAX_EXECUTION_TIME, MAX_UPLOAD_SIZE
)
from models import CodeSubmission, JobStatus
from services.job_service import (
    job_status, allowed_file, create_job, 
    get_job_status, delete_job
)
from services.sandbox_service import execute_code_in_sandbox, get_code_template
from services.cleanup_service import cleanup_old_jobs, cleanup_job_files

@asynccontextmanager
async def lifespan(app: FastAPI):
    # background task when app starts
    cleanup_task = asyncio.create_task(cleanup_old_jobs())
    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="File Processor API",
    description="API for secure CSV/Excel file processing with Python in a sandboxed environment",
    lifespan=lifespan
)

@app.post("/upload", response_model=Dict[str, str], 
          summary="Upload a CSV or Excel file for processing")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel file for processing.
    
    Returns a job ID that can be used to submit code and retrieve results.
    """
    # Checking if file is valid
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 
    filename = os.path.basename(file.filename)
    job_id = create_job(filename, "")  # Create job first to get ID
    file_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{filename}")
    
    # save uploaded file
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        delete_job(job_id)
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE/1024/1024}MB")
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Update job with file path
    job_status[job_id]['file_path'] = file_path
    
    return {
        'job_id': job_id,
        'status': 'uploaded',
        'message': 'File uploaded successfully'
    }

@app.post("/submit_code/{job_id}", response_model=Dict[str, str],
          summary="Submit Python code to process the uploaded file")
async def submit_code(
    job_id: str, 
    code_submission: CodeSubmission,
    background_tasks: BackgroundTasks
):
    """
     Python code to process the previously uploaded file.
    
    The code will be executed in a sandboxed Docker container with access to the uploaded file.
    """
    # Check if the job exists
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        code_path = os.path.join(CODE_FOLDER, f"{job_id}_process.py")
        with open(code_path, 'w') as code_file:
            code_file.write(code_submission.code)
        
        
        result_path = os.path.join(RESULTS_FOLDER, job_id)
        os.makedirs(result_path, exist_ok=True)
        
        
        job_status[job_id]['status'] = 'processing'
        job_status[job_id]['code_path'] = code_path
        job_status[job_id]['result_path'] = result_path
        
        # Execute the code in background
        file_path = job_status[job_id]['file_path']
        background_tasks.add_task(
            execute_code_in_sandbox,
            job_id, file_path, code_path, result_path, MAX_EXECUTION_TIME
        )
        
        return {
            'job_id': job_id,
            'status': 'processing',
            'message': 'Code submitted and processing started'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing code: {str(e)}")

@app.get("/status/{job_id}", response_model=Dict[str, Any],
         summary="Check the status of a processing job")
async def get_status(job_id: str):
    """
    Get the current status of a file processing job.
    """

    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]

@app.get("/results/{job_id}", 
         summary="Get the results of a completed processing job")
async def get_results(
    job_id: str, 
    output_format: str = Query("json", description="Output format (json, csv, excel)")
):
    """
    Get the results of a completed file processing job.
    
    The results can be retrieved in different formats: JSON, CSV, or Excel.
    """
    # Check if the job exists
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if job is completed
    if job_status[job_id]['status'] != 'completed':
        return JSONResponse(
            status_code=400,
            content={
                'status': job_status[job_id]['status'],
                'message': 'Results not available yet'
            }
        )
    
    result_path = job_status[job_id]['result_path']
    
    # Check if results exist
    result_files = [f for f in os.listdir(result_path) if os.path.isfile(os.path.join(result_path, f))]
    
    if not result_files:
        raise HTTPException(status_code=404, detail="No results found")
    
    # Return based on requested for format
    if output_format == 'csv':
        # Find CSV files
        csv_files = [f for f in result_files if f.endswith('.csv')]
        if csv_files:
            return FileResponse(
                path=os.path.join(result_path, csv_files[0]),
                media_type='text/csv',
                filename=f"result_{job_id}.csv"
            )
    
    elif output_format == 'excel':
        # Find Excel files
        excel_files = [f for f in result_files if f.endswith(('.xlsx', '.xls'))]
        if excel_files:
            return FileResponse(
                path=os.path.join(result_path, excel_files[0]),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=f"result_{job_id}.xlsx"
            )
    
    # Default: return JSON
    json_files = [f for f in result_files if f.endswith('.json')]
    if json_files:
        with open(os.path.join(result_path, json_files[0]), 'r') as f:
            return JSONResponse(content=json.load(f))
    
    # If no specific format file found, return the first result
    return FileResponse(
        path=os.path.join(result_path, result_files[0]),
        filename=f"result_{job_id}_{result_files[0]}"
    )

@app.delete("/cleanup/{job_id}", response_model=Dict[str, str],
            summary="Clean up files and data associated with a job")
async def cleanup_job(job_id: str):
    """
    Delete all files and data associated with a job.
    """
    # Check if the job exists
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # files cleanup
    try:
        success = await cleanup_job_files(job_id)
        if success:
            delete_job(job_id)
            return {'message': f'Job {job_id} cleaned up successfully'}
        else:
            raise HTTPException(status_code=500, detail="Error cleaning up job files")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up job: {str(e)}")

@app.get("/template", response_model=Dict[str, str],
         summary="Get a code template for file processing")
async def get_template():
    """
    Get a template Python code for processing files.
    """
    return {'template': get_code_template()}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)