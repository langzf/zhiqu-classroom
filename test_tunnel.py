import requests

# Test student frontend
r = requests.get('https://tricks-wheat-culture-level.trycloudflare.com/', timeout=10)
print(f'Student Frontend Status: {r.status_code}')
print(f'Content-Type: {r.headers.get("content-type")}')

# Test API proxy
r2 = requests.get('https://tricks-wheat-culture-level.trycloudflare.com/api/v1/health', timeout=10)
print(f'\nAPI Proxy Status: {r2.status_code}')
print(f'Response: {r2.text}')

# Test admin frontend
r3 = requests.get('https://elephant-explicitly-real-late.trycloudflare.com/', timeout=10)
print(f'\nAdmin Frontend Status: {r3.status_code}')
print(f'Content-Type: {r3.headers.get("content-type")}')

# Test admin API proxy
r4 = requests.get('https://elephant-explicitly-real-late.trycloudflare.com/api/v1/health', timeout=10)
print(f'\nAdmin API Proxy Status: {r4.status_code}')
print(f'Response: {r4.text}')
