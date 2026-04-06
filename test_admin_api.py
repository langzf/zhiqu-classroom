import requests

# Login to get token
login_data = {"phone": "13800000001"}
r = requests.post('http://localhost:8001/api/v1/user/login', json=login_data)
print(f'Login Status: {r.status_code}')
if r.status_code == 200:
    token = r.json()['data']['access_token']
    print(f'Token: {token[:50]}...')
    
    # Test admin endpoints
    headers = {'Authorization': f'Bearer {token}'}
    
    # List textbooks
    r2 = requests.get('http://localhost:8001/content/textbooks', headers=headers)
    print(f'\nList Textbooks Status: {r2.status_code}')
    print(f'Response: {r2.text[:200]}')
    
    # List conversations
    r3 = requests.get('http://localhost:8001/api/v1/admin/tutor/conversations', headers=headers)
    print(f'\nList Conversations Status: {r3.status_code}')
    print(f'Response: {r3.text[:200]}')
    
    # List tasks
    r4 = requests.get('http://localhost:8001/learning/tasks', headers=headers)
    print(f'\nList Tasks Status: {r4.status_code}')
    print(f'Response: {r4.text[:200]}')
else:
    print(f'Login failed: {r.text}')
