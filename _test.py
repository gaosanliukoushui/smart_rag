import requests

r = requests.post('http://localhost:3000/api/v1/auth/login', json={'username':'testuser','password':'Test1234!'}, timeout=10)
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

kb = '139d254c-d29d-4eac-97ca-efcf9e7c0055'
r = requests.get(f'http://localhost:3000/api/v1/documents', headers=headers, params={'knowledge_base_id': kb}, timeout=10)
docs = r.json()['documents']
print(f"Documents ({len(docs)}): {[d['id'][:8] for d in docs]}")

if docs:
    doc_id = docs[0]['id']
    print(f"\nDeleting: {doc_id}")
    r = requests.delete(f'http://localhost:3000/api/v1/documents/{doc_id}', headers=headers, timeout=10)
    print(f"Delete status: {r.status_code}")

    r = requests.get(f'http://localhost:3000/api/v1/documents', headers=headers, params={'knowledge_base_id': kb}, timeout=10)
    print(f"Remaining docs: {len(r.json()['documents'])}")
