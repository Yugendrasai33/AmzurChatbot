"""
End-to-end test for the RAG pipeline:
  1. Login to get auth token
  2. Create a thread
  3. Upload a PDF file
  4. Ingest the PDF into ChromaDB via /api/rag/ingest
  5. Query the RAG endpoint via /api/rag/stream (SSE)
  6. Verify the response is grounded in the PDF content
"""

import json
import sys
import httpx

BASE = "http://localhost:8000"
PASS_SYMBOL = "PASS"
FAIL_SYMBOL = "FAIL"

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    status = PASS_SYMBOL if passed else FAIL_SYMBOL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # ─── Step 0: Authenticate ───────────────────────────────────────
    print("\n=== Step 0: Authenticate (local JWT) ===")
    try:
        # Use an existing user profile from the database
        test_user_id = "60c6d1c0-cd68-479e-8312-8a1d6a2c5c44"
        test_email = "sai123@stackyon.com"
        from app.services.auth_service import issue_local_jwt
        token = issue_local_jwt(test_user_id, test_email)
        record("Generate local JWT", True, f"user_id={test_user_id[:12]}..., token={token[:20]}...")
    except Exception as e:
        record("Generate local JWT", False, str(e))
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # ─── Step 1: Create a thread ─────────────────────────────────────
    print("\n=== Step 1: Create Thread ===")
    try:
        r = httpx.post(f"{BASE}/api/threads", json={"title": "RAG Test Thread"}, headers=headers, timeout=15)
        if r.status_code == 200:
            thread = r.json()
            thread_id = thread["id"]
            record("Create Thread", True, f"thread_id={thread_id}")
        else:
            record("Create Thread", False, f"Status {r.status_code}: {r.text[:200]}")
            sys.exit(1)
    except Exception as e:
        record("Create Thread", False, str(e))
        sys.exit(1)

    # ─── Step 2: Upload PDF ──────────────────────────────────────────
    print("\n=== Step 2: Upload PDF ===")
    try:
        with open("test_document.pdf", "rb") as f:
            r = httpx.post(
                f"{BASE}/api/chat/upload",
                files={"file": ("test_document.pdf", f, "application/pdf")},
                headers=headers,
                timeout=30,
            )
        if r.status_code == 200:
            upload_data = r.json()
            attachment_id = upload_data["id"]
            record("Upload PDF", True, f"attachment_id={attachment_id}, size={upload_data.get('size_bytes')} bytes")
            record("Upload - MIME type", upload_data.get("mime_type") == "application/pdf",
                   f"mime_type={upload_data.get('mime_type')}")
            record("Upload - Category", upload_data.get("type_category") == "pdf",
                   f"type_category={upload_data.get('type_category')}")
        else:
            record("Upload PDF", False, f"Status {r.status_code}: {r.text[:200]}")
            sys.exit(1)
    except Exception as e:
        record("Upload PDF", False, str(e))
        sys.exit(1)

    # ─── Step 3: Ingest into ChromaDB ────────────────────────────────
    print("\n=== Step 3: Ingest PDF into ChromaDB ===")
    try:
        r = httpx.post(
            f"{BASE}/api/rag/ingest/{attachment_id}",
            headers=headers,
            timeout=60,
        )
        if r.status_code == 200:
            ingest_data = r.json()
            chunks = ingest_data.get("chunks_ingested", 0)
            record("Ingest PDF", True, f"chunks_ingested={chunks}")
            record("Ingest - Has chunks", chunks > 0, f"{chunks} chunks created")
            record("Ingest - Attachment ID match",
                   ingest_data.get("attachment_id") == attachment_id,
                   f"returned={ingest_data.get('attachment_id')}")
        else:
            record("Ingest PDF", False, f"Status {r.status_code}: {r.text[:300]}")
            sys.exit(1)
    except Exception as e:
        record("Ingest PDF", False, str(e))
        sys.exit(1)

    # ─── Step 4: Query via RAG stream (SSE) ──────────────────────────
    print("\n=== Step 4: RAG Query (SSE Stream) ===")
    test_queries = [
        ("What is the remote work policy?", ["remote", "3 days", "core hours"]),
        ("How many PTO days do employees get?", ["20", "paid", "leave"]),
        ("What is the training budget?", ["2,500", "2500", "professional"]),
    ]

    for query, expected_keywords in test_queries:
        print(f"\n  Query: \"{query}\"")
        try:
            with httpx.stream(
                "POST",
                f"{BASE}/api/rag/stream",
                json={"thread_id": thread_id, "message": query},
                headers={**headers, "Content-Type": "application/json"},
                timeout=90,
            ) as stream:
                if stream.status_code != 200:
                    body = stream.read().decode()
                    record(f"RAG Query: {query[:40]}", False,
                           f"Status {stream.status_code}: {body[:200]}")
                    continue

                full_response = ""
                token_count = 0
                for line in stream.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    full_response += payload
                    token_count += 1

            record(f"RAG Stream received tokens", token_count > 0,
                   f"{token_count} tokens, {len(full_response)} chars")
            record(f"RAG Response not empty", len(full_response.strip()) > 0,
                   f"Response: {full_response[:120]}...")

            # Check if response contains expected keywords (grounded in PDF)
            response_lower = full_response.lower()
            found = [kw for kw in expected_keywords if kw.lower() in response_lower]
            grounded = len(found) > 0
            record(f"RAG Grounded: {query[:35]}",
                   grounded,
                   f"Found keywords: {found}" if grounded else f"None of {expected_keywords} found in response")

        except Exception as e:
            record(f"RAG Query: {query[:40]}", False, str(e))

    # ─── Step 5: Test edge case — query without documents ────────────
    print("\n=== Step 5: Edge Case — No documents user ===")
    # We can't easily test a different user, but we can verify the endpoint handles errors gracefully

    # ─── Step 6: Test ingest with non-existent attachment ────────────
    print("\n=== Step 6: Edge Case — Non-existent attachment ===")
    try:
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = httpx.post(
            f"{BASE}/api/rag/ingest/{fake_id}",
            headers=headers,
            timeout=15,
        )
        record("Ingest non-existent - Returns 404", r.status_code == 404,
               f"Status {r.status_code}")
    except Exception as e:
        record("Ingest non-existent", False, str(e))

    # ─── Step 7: Test auth required ──────────────────────────────────
    print("\n=== Step 7: Auth Required ===")
    try:
        r = httpx.post(f"{BASE}/api/rag/ingest/{attachment_id}", timeout=15)
        record("Ingest without auth - Returns 401", r.status_code == 401,
               f"Status {r.status_code}")
    except Exception as e:
        record("Auth check", False, str(e))

    try:
        r = httpx.post(
            f"{BASE}/api/rag/stream",
            json={"thread_id": thread_id, "message": "test"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        record("Stream without auth - Returns 401", r.status_code == 401,
               f"Status {r.status_code}")
    except Exception as e:
        record("Auth check stream", False, str(e))

    # ─── Summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n  Failed tests:")
        for name, p, detail in results:
            if not p:
                print(f"    [{FAIL_SYMBOL}] {name}: {detail}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
