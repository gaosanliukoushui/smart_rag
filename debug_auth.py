import sys, os, traceback
os.chdir('e:/我的项目/SmartRAG')
sys.path.insert(0, 'e:/我的项目/SmartRAG')

# Simulate the /auth/me request flow
print("=== Step 1: Import modules ===")
from app.api.deps import get_db, get_current_user, get_current_active_user
from app.core.security import decode_access_token
import uuid

print("=== Step 2: Login to get a valid token ===")
from app.db.session import get_db as _get_db_session
db = next(_get_db_session())
from app.services.auth_service import AuthService
from app.schemas.auth import UserLogin
service = AuthService(db)
user = service.authenticate(UserLogin(username="testuser", password="Test1234!"))
tokens = service.create_tokens(user)
access = tokens['access_token']
print("Token:", access[:40], "...")
db.close()

print("=== Step 3: Decode token ===")
payload = decode_access_token(access)
print("Payload:", payload)

print("=== Step 4: Lookup user from DB ===")
db2 = next(_get_db_session())
user_id = uuid.UUID(payload['sub'])
from sqlalchemy import select
from app.models import User
stmt = select(User).where(User.id == user_id)
found_user = db2.execute(stmt).scalar_one_or_none()
print("User found:", found_user.username, found_user.email if found_user else None)
db2.close()

print("=== Step 5: Get user response ===")
resp = service.get_user_response(found_user)
print("Response:", resp)

print()
print("=== All steps passed! No crash. ===")
