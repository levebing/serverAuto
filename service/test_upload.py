import requests
import time

time.sleep(2)

try:
    r = requests.post('http://localhost:5000/api/upload', files={'file': ('test.txt', 'hello world', 'text/plain')})
    print(r.json())
except Exception as e:
    print(f"Error: {e}")