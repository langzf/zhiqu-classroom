import requests

# Login via backend tunnel
login_data = {"phone": "13800000001"}
r = requests.post('https://copy-novel-remain-ram.trycloudflare.com/api/v1/user/login', json=login_data)
print(f'Login Status: {r.status_code}')
token = r.json()['data']['access_token']
print(f'Token: {token[:50]}...')

headers = {'Authorization': f'Bearer {token}'}

# Test admin endpoints
endpoints = [
    '/api/v1/admin/content/textbooks',
    '/api/v1/admin/learning/tasks',
    '/api/v1/admin/tutor/conversations',
]

for endpoint in endpoints:
    r = requests.get(f'https://copy-novel-remain-ram.trycloudflare.com{endpoint}', headers=headers)
    print(f'\n{endpoint}: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'  Data keys: {list(data.keys())}')
    else:
        print(f'  Error: {r.text[:100]}')
