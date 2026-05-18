"""Debug: check what's actually in the vector store and trace the full retrieval path."""
import asyncio
import sys
import io
sys.path.insert(0, '.')

import httpx
import os
os.environ.setdefault("ENVIRONMENT", "development")

async def main():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
        # Login
        login_resp = await client.post("/api/v1/auth/login", json={
            "username": "debug_user",
            "password": "debugpass123"
        })
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            return
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get KB
        kbs = (await client.get("/api/v1/knowledge-bases", headers=headers)).json()["knowledge_bases"]
        if not kbs:
            print("No KBs found!")
            return
        kb_id = kbs[0]["id"]
        print(f"KB ID: {kb_id}")

        # Upload doc
        content = b"John Doe is a senior Python developer with 5 years of experience in AI and ML."
        upload_resp = await client.post(
            f"/api/v1/documents/upload?knowledge_base_id={kb_id}",
            files={"file": ("resume.txt", io.BytesIO(content), "text/plain")},
            headers=headers,
        )
        print(f"Upload: {upload_resp.status_code} => {upload_resp.json()}")

        # Also check: manually query vector store
        print("\n--- Checking vector store directly ---")
        from app.services.vector_store_service import get_vector_store
        vs = get_vector_store()
        print(f"Total vectors: {len(vs._embeddings)}")
        for vid, data in vs._embeddings.items():
            print(f"  [{vid[:8]}...] kb_id={data['metadata'].get('knowledge_base_id')}, text={data['text'][:60]}")

        # Now chat
        print("\n--- Chat test ---")
        chat_resp = await client.post(
            "/api/v1/chat",
            json={"knowledge_base_id": kb_id, "message": "Who is John Doe?", "stream": False},
            headers=headers,
            timeout=30.0,
        )
        print(f"Chat status: {chat_resp.status_code}")
        if chat_resp.status_code == 200:
            data = chat_resp.json()
            print(f"Answer: {data.get('answer', '')[:200]}")
            sources = data.get('sources', [])
            print(f"Sources count: {len(sources)}")
            for s in sources:
                print(f"  - score={s.get('score')}, content={s.get('content', '')[:100]}")
        else:
            print(f"Error: {chat_resp.text[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
