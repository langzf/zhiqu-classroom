import requests

# Test student login endpoint (correct endpoint)
response = requests.post(
    'https://copy-novel-remain-ram.trycloudflare.com/api/v1/user/login',
    json={'phone': '18457113512'}
)

print(f'Status: {response.status_code}')
print(f'Response: {response.text}')
