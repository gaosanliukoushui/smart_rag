import urllib.request, json

base = 'http://localhost:8000'

# 1. Login
data = json.dumps({'username': 'testuser', 'password': 'Test1234!'}).encode()
req = urllib.request.Request(base + '/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    tokens = json.loads(r.read())
access = tokens['access_token']
print('[PASS] 1. Login OK, expires_in:', tokens['expires_in'])

# 2. Auth/Me
req2 = urllib.request.Request(base + '/api/v1/auth/me', headers={'Authorization': 'Bearer ' + access})
with urllib.request.urlopen(req2) as r:
    user = json.loads(r.read())
print('[PASS] 2. Auth/Me OK:', user['username'], '/', user['email'])

# 3. Knowledge bases list
req3 = urllib.request.Request(base + '/api/v1/knowledge-bases', headers={'Authorization': 'Bearer ' + access})
with urllib.request.urlopen(req3) as r:
    kb_response = json.loads(r.read())
kbs = kb_response['knowledge_bases']
print('[PASS] 3. Knowledge Bases list OK:', len(kbs), 'item(s), total:', kb_response['total'])
for kb in kbs:
    print('     -', kb['name'], '(id=' + kb['id'] + ')')

# 4. Create a new KB
data4 = json.dumps({'name': 'Test KB', 'description': 'A test knowledge base'}).encode()
req4 = urllib.request.Request(base + '/api/v1/knowledge-bases', data=data4, headers={'Authorization': 'Bearer ' + access, 'Content-Type': 'application/json'})
with urllib.request.urlopen(req4) as r:
    kb_new = json.loads(r.read())
print('[PASS] 4. KB Created:', kb_new['name'], '(id=' + kb_new['id'] + ')')

# 5. Health
with urllib.request.urlopen(base + '/api/v1/health') as r:
    health = json.loads(r.read())
print('[PASS] 5. Health:', health)

print()
print('All tests passed!')
