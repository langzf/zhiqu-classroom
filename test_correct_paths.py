import requests

# Login
login_data = {"phone": "13800000001"}
r = requests.post('http://localhost:8001/api/v1/user/login', json=login_data)
token = r.json()['data']['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Test correct paths
endpoints = [
    '/api/v1/admin/content/textbooks',
    '/api/v1/admin/learning/tasks',
    '/api/v1/admin/tutor/conversations',
]

for endpoint in endpoints:
    r = requests.get(f'http://localhost:8001{endpoint}', headers=headers)
    print(f'{endpoint}: {r.status_code}')
    if r.status_code != 200:
        print(f'  Error: {r.text[:100]}')
