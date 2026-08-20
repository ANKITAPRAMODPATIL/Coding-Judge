import os
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onlinejudge.settings')
django.setup()

from django.core.cache import cache

try:
   
    cache.set('test_key', 'Redis is working perfectly!', timeout=60)
    
  
    val = cache.get('test_key')
    print("SUCCESS:", val)
except Exception as e:
    print("ERROR:", e)
