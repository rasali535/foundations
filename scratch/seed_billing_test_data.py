import asyncio
import os
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "foundations_db")
API_BASE = "http://127.0.0.1:8000/api"

async def seed_billing_test():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("[1] Setting up FCA Billing Test Organisation...")
    org_id = "test-billing-org-12345"
    org_data = {
        "id": org_id,
        "name": "FCA Billing Test Organisation",
        "code": "FCA-BILL-TEST",
        "status": "active",
        "contract_start": "2026-01-01",
        "contract_end": "2026-12-31",
        "allocated_sessions": 100,
        "contact_person": "Finance Director",
        "contact_email": "billing@fcabill.local",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.organisations.update_one({"id": org_id}, {"$set": org_data}, upsert=True)

    # Synthetic client
    client_id = "client-billing-synthetic-1"
    client_data = {
        "id": client_id,
        "client_number": "FCA-SYNTH-BILL-01",
        "first_name": "SyntheticClientFirst",
        "last_name": "SyntheticClientLast",
        "email": "synthetic_client@fcabill.local",
        "phone": "+26771999111",
        "organisation_id": org_id,
        "organisation_name": "FCA Billing Test Organisation",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.crm_clients.update_one({"id": client_id}, {"$set": client_data}, upsert=True)

    # Clean up any existing bookings for this client
    await db.bookings.delete_many({"client_id": client_id})
    await db.invoices.delete_many({"organisation_id": org_id})
    await db.invoice_items.delete_many({"invoice_id": {"$regex": "^test-inv"}})

    print("[2] Creating 10 Individual, 3 Couple, 2 Family completed sessions...")
    bookings = []
    # 10 Individual
    for i in range(10):
        day = String = f"{i+1:02d}"
        bookings.append({
            "id": f"bill-book-ind-{i+1}",
            "client_id": client_id,
            "therapist_id": "th-caroline-sithole",
            "therapist_name": "Caroline Sithole",
            "session_type": "individual",
            "session_mode": "in_person",
            "starts_at": f"2026-09-{day}T09:00:00Z",
            "ends_at": f"2026-09-{day}T10:00:00Z",
            "status": "completed",
            "active_invoice_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    # 3 Couple
    for i in range(3):
        day = f"{11+i:02d}"
        bookings.append({
            "id": f"bill-book-cpl-{i+1}",
            "client_id": client_id,
            "therapist_id": "th-kagiso-moeti",
            "therapist_name": "Kagiso Moeti",
            "session_type": "couple",
            "session_mode": "in_person",
            "starts_at": f"2026-09-{day}T11:00:00Z",
            "ends_at": f"2026-09-{day}T12:00:00Z",
            "status": "completed",
            "active_invoice_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    # 2 Family
    for i in range(2):
        day = f"{14+i:02d}"
        bookings.append({
            "id": f"bill-book-fam-{i+1}",
            "client_id": client_id,
            "therapist_id": "th-thabo-kgosi",
            "therapist_name": "Dr. Thabo Kgosi",
            "session_type": "family",
            "session_mode": "virtual",
            "starts_at": f"2026-09-{day}T14:00:00Z",
            "ends_at": f"2026-09-{day}T15:00:00Z",
            "status": "completed",
            "active_invoice_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    await db.bookings.insert_many(bookings)
    print(f"Inserted {len(bookings)} completed sessions into MongoDB.")

    # Now validate through live API
    s = requests.Session()
    print("[3] Authenticating as Admin against live API...")
    login_res = s.post(f"{API_BASE}/login", json={"username": "admin", "password": "adminpass123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    print("[4] Testing Live Preview Endpoint...")
    prev_res = s.get(
        f"{API_BASE}/invoices/preview",
        params={
            "organisation_id": org_id,
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        }
    )
    assert prev_res.status_code == 200, f"Preview failed: {prev_res.text}"
    prev_data = prev_res.json()
    print("Preview Result:", prev_data)
    assert prev_data["total_sessions"] == 15
    assert prev_data["total"] == 6500.0, f"Expected 6500.0, got {prev_data['total']}"

    item_map = {it["session_type"]: it for it in prev_data["items"]}
    assert item_map["individual"]["quantity"] == 10
    assert item_map["individual"]["line_total"] == 3500.0
    assert item_map["couple"]["quantity"] == 3
    assert item_map["couple"]["line_total"] == 1800.0
    assert item_map["family"]["quantity"] == 2
    assert item_map["family"]["line_total"] == 1200.0
    print("✓ Preview calculations verified: 10 Ind x 350 = 3500, 3 Cpl x 600 = 1800, 2 Fam x 600 = 1200 -> TOTAL BWP 6,500.00")

    print("[5] Generating Draft Invoice via Live API...")
    gen_res = s.post(f"{API_BASE}/invoices", json={
        "organisation_id": org_id,
        "billing_period_start": "2026-09-01",
        "billing_period_end": "2026-09-30",
        "due_date": "2026-10-15"
    })
    assert gen_res.status_code == 201, f"Generate invoice failed: {gen_res.text}"
    gen_data = gen_res.json()
    inv = gen_data["invoice"]
    inv_id = inv["id"]
    inv_num = inv["invoice_number"]
    print(f"✓ Invoice created: {inv_num} (ID: {inv_id}, Status: {inv['status']}, Total: BWP {inv['total']})")

    print("[6] Issuing Invoice...")
    issue_res = s.post(f"{API_BASE}/invoices/{inv_id}/issue")
    assert issue_res.status_code == 200, f"Issue failed: {issue_res.text}"
    issued_inv = issue_res.json()
    assert issued_inv["status"] == "issued"
    assert issued_inv["issued_at"] is not None
    print(f"✓ Invoice issued at {issued_inv['issued_at']}")

    print("[7] Downloading Invoice PDF...")
    pdf_res = s.get(f"{API_BASE}/invoices/{inv_id}/pdf")
    assert pdf_res.status_code == 200, f"PDF download failed: {pdf_res.text}"
    assert pdf_res.headers.get("content-type") == "application/pdf"
    pdf_bytes = pdf_res.content
    assert pdf_bytes.startswith(b"%PDF-")
    print(f"✓ PDF downloaded successfully ({len(pdf_bytes)} bytes)")

    # Save artifact
    out_pdf_path = os.path.join(os.path.dirname(__file__), "FCA_Test_Invoice.pdf")
    with open(out_pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"✓ PDF saved to {out_pdf_path}")

    # Inspect PDF for sensitive strings
    assert b"SyntheticClientFirst" not in pdf_bytes
    assert b"SyntheticClientLast" not in pdf_bytes
    assert b"synthetic_client@fcabill.local" not in pdf_bytes
    assert b"+26771999111" not in pdf_bytes
    assert b"FCA-SYNTH-BILL-01" not in pdf_bytes
    assert b"bill-book-ind-1" not in pdf_bytes
    print("✓ Strict privacy check passed: ZERO client PII in generated PDF.")

    print("\n==========================================")
    print("SUCCESS: Live validation of test invoice complete!")
    print(f"Invoice Number: {inv_num}")
    print("Total Sessions: 15 (10 Individual, 3 Couple, 2 Family)")
    print("Total Amount:   BWP 6,500.00")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(seed_billing_test())
