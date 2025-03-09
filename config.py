import os
import tempfile

# Configuration
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'file_processor', 'uploads')
CODE_FOLDER = os.path.join(tempfile.gettempdir(), 'file_processor', 'code')
RESULTS_FOLDER = os.path.join(tempfile.gettempdir(), 'file_processor', 'results')
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
MAX_EXECUTION_TIME = 120  # seconds
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB limit

# directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CODE_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)