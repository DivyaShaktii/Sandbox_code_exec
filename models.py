from typing import Dict, List, Optional, Any
from pydantic import BaseModel, field_validator

class CodeSubmission(BaseModel):
    code: str
    
    @field_validator('code')
    def validate_code(cls, v):
        forbidden_modules = [
            'subprocess', 'os.system', 'eval(', 'exec(', 'importlib', 
            'sys.modules', '__import__', 'open(', 'file(', 
            'execfile(', 'compile(', 'pty', 'popen', 'system'
        ]
        
        for module in forbidden_modules:
            if module in v:
                raise ValueError(f"Forbidden module or function detected: {module}")
        return v

class JobStatus(BaseModel):
    id: str
    filename: str
    status: str
    timestamp: str
    error: Optional[str] = None