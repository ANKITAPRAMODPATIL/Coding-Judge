from django.test import TestCase


import subprocess
import tempfile
import os
from celery import shared_task

@shared_task
def execute_code_task(submission_id, code, test_input=""):
    """
    User ke code ko ek temporary file mein likhkar securely execute karega.
    """
   
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        
        result = subprocess.run(
            ['python', temp_file_path],
            input=test_input,
            text=True,
            capture_output=True,
            timeout=5 
        )
        
        output = result.stdout
        error = result.stderr
        exit_code = result.returncode

    except subprocess.TimeoutExpired:
        output = ""
        error = "Time Limit Exceeded (TLE): Code took too long to execute."
        exit_code = -1
    except Exception as e:
        output = ""
        error = str(e)
        exit_code = -1
    finally:
        
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    
    print(f"Submission {submission_id} executed. Exit code: {exit_code}")
    print(f"Output: {output}")
    print(f"Error: {error}")

    return {
        "exit_code": exit_code,
        "output": output,
        "error": error

    }



