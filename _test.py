import requests

r = requests.post('http://localhost:3000/api/v1/auth/login', json={'username':'testuser','password':'Test1234!'}, timeout=10)
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get('http://localhost:3000/api/v1/chat/sessions', headers=headers, timeout=10)
result = r.json()
sessions = result.get('sessions', [])
print(f"Status: {r.status_code}, Sessions count: {len(sessions)}")

if sessions:
    sid = sessions[0]['session_id']
    print(f"\nFetching history for: {sid}")
    r2 = requests.get(f'http://localhost:3000/api/v1/chat/history/{sid}', headers=headers, timeout=10)
    print(f"History status: {r2.status_code}")
    print(f"History body: {r2.text[:500]}")
