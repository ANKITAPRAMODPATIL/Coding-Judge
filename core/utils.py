from judge.models import AuditLog
from difflib import SequenceMatcher

def log_user_action(user, action, request=None, details=""):
    try:
        ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

       
        print(f">>> SAVING AUDIT LOG: User={user}, Action={action}, Details={details}")

        log_entry = AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            ip_address=ip,
            details=details
        )
        print(f">>> SUCCESS! Audit Log created with ID: {log_entry.id}")
        
    except Exception as e:
        print(f">>> ERROR IN AUDIT LOG: {e}")

def is_plagiarism(new_code, existing_submissions):
    for sub in existing_submissions:
        
        similarity = SequenceMatcher(None, new_code, sub.code).ratio()
        if similarity > 0.9:  
            return True
    return False        
