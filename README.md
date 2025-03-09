### Build the Docker Container
`docker build -t python-sandbox .`

### Run the Application
`python app.py`

### API Endpoints

#### POST Methods

1. **POST `/upload`**
   - Upload a CSV or Excel file for processing
   - Returns a job ID for tracking the processing
   - File size limits and format restrictions apply

2. **POST `/submit_code/{job_id}`**
   - Submit Python code to process the previously uploaded file
   - Code runs in a sandboxed Docker container
   - Requires valid job_id from upload endpoint
   - Returns processing status

#### GET Methods

1. **GET `/status/{job_id}`**
   - Check the current status of a processing job
   - Returns job status and related information

2. **GET `/results/{job_id}`**
   - Retrieve results of a completed processing job
   - Supports multiple output formats (json, csv, excel)
   - Query parameter: `output_format` (default: json)

3. **GET `/template`**
   - Get a template Python code for file processing
   - Returns a starter code template for processing files

#### DELETE Methods

1. **DELETE `/cleanup/{job_id}`**
   - Clean up all files and data associated with a job
   - Removes temporary files and job status information

* 