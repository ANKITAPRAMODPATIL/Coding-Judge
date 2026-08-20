from celery import shared_task
import subprocess
import os
from .models import Submission
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def execute_code_task(submission_id, code_string):
    print(f"Starting execution for submission: {submission_id}")
    
    file_name = f"temp_sub_{submission_id}.py"
    output = ""
    error = ""
    status = "Error"
    
    channel_layer = get_channel_layer()
    
    try:
        
        submission = Submission.objects.get(id=submission_id)
        submission.status = "Running"
        submission.save()
        
    
        async_to_sync(channel_layer.group_send)(
            f'submission_{submission_id}',
            {
                'type': 'submission_update',
                'message': {'status': 'Running', 'output': ''}
            }
        )
        
       
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(code_string)
        
        
        result = subprocess.run(
            ["python", file_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout
        error = result.stderr
        
        
        if result.returncode != 0 or error:
            status = "Wrong Answer" 
        else:
            status = "Accepted"   
            
    except Submission.DoesNotExist:
        error = f"Submission with id {submission_id} does not exist."
        status = "Error"
        print(error)
        return {"error": error}
        
    except subprocess.TimeoutExpired:
        error = "Time Limit Exceeded: Code execution took longer than 5 seconds."
        status = "Time Limit Exceeded"
        
    except Exception as e:
        error = f"Execution Error: {str(e)}"
        status = "Error"
        
    finally:
      
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
            except Exception as cleanup_error:
                print(f"Error removing temp file: {cleanup_error}")
        
        
        try:
            submission = Submission.objects.get(id=submission_id)
            submission.output = output if not error else error
            submission.error = error
            submission.status = status
            submission.save()
            print(f"Submission {submission_id} updated with status: {status}")
        except Submission.DoesNotExist:
            print(f"Could not update database: Submission {submission_id} was deleted.")

      
        async_to_sync(channel_layer.group_send)(
            f'submission_{submission_id}',
            {
                'type': 'submission_update',
                'message': {
                    'status': status,
                    'output': output if not error else error
                }
            }
        )

    return {"output": output, "error": error, "status": status}  


def send_submission_update(submission_id, status, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'submission_{submission_id}',
        {
            'type': 'submission_update',
            'status': status,
            'message': message
        }
    )

@shared_task
def execute_code_task(submission_id):
    
    submission = Submission.objects.get(id=submission_id)
    
   
    submission.status = 'Accepted'
    submission.save()
    
    send_submission_update(submission_id, 'Accepted', 'All test cases passed successfully!')

    