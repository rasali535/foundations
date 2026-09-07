from fastapi import APIRouter, HTTPException, Depends, Request, status, Query, Response
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import (
    Invoice,
    InvoiceItem,
    InvoicePreviewResponse,
    InvoiceCreateRequest,
    InvoiceCancelRequest
)
from services.billing_service import BillingService
from services.audit_service import AuditService

invoice_router = APIRouter(tags=["Invoicing"])

def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

def get_current_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {
        "user_id": user_id,
        "role": role,
        "name": request.session.get("name", user_id),
        "organisation_id": request.session.get("organisation_id")
    }

def require_admin(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin billing access required")
    return user

def require_hr_user(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if user.get("role") not in ["hr_admin", "hr_viewer", "super_admin", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Corporate HR access required")
    org_id = user.get("organisation_id")
    if user.get("role") in ["hr_admin", "hr_viewer"] and not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No corporate organisation associated with HR account")
    return user

# ==================== Admin Invoice Endpoints ====================

@invoice_router.get("/invoices/preview", response_model=InvoicePreviewResponse)
async def preview_invoice(
    request: Request,
    organisation_id: str = Query(..., description="ID of organisation to bill"),
    billing_period_start: str = Query(..., description="YYYY-MM-DD"),
    billing_period_end: str = Query(..., description="YYYY-MM-DD"),
    user: Dict = Depends(require_admin)
):
    """
    Live preview of completed uninvoiced sessions for an organisation.
    """
    db = get_db(request)
    return await BillingService.preview_invoice(
        db, organisation_id, billing_period_start, billing_period_end
    )

@invoice_router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_draft_invoice(
    request: Request,
    payload: InvoiceCreateRequest,
    user: Dict = Depends(require_admin)
):
    """
    Generate draft corporate invoice from completed uninvoiced sessions.
    """
    db = get_db(request)
    invoice, items = await BillingService.create_draft_invoice(
        db=db,
        organisation_id=payload.organisation_id,
        start_date=payload.billing_period_start,
        end_date=payload.billing_period_end,
        due_date=payload.due_date,
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    return {
        "invoice": invoice.model_dump(),
        "items": [it.model_dump() for it in items]
    }

@invoice_router.get("/invoices", response_model=List[Invoice])
async def list_invoices(
    request: Request,
    organisation_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    user: Dict = Depends(require_admin)
):
    """
    List all corporate invoices with multi-attribute filtering.
    """
    db = get_db(request)
    query: Dict[str, Any] = {}
    if organisation_id:
        query["organisation_id"] = organisation_id
    if status_filter and status_filter.lower() != "all":
        query["status"] = status_filter.lower()
    if start_date:
        query["billing_period_start"] = {"$gte": start_date}
    if end_date:
        query["billing_period_end"] = {"$lte": end_date}
    if search:
        query["$or"] = [
            {"invoice_number": {"$regex": search, "$options": "i"}},
            {"organisation_name": {"$regex": search, "$options": "i"}}
        ]

    docs = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return docs

@invoice_router.get("/invoices/{invoice_id}")
async def get_invoice_detail(
    request: Request,
    invoice_id: str,
    user: Dict = Depends(require_admin)
):
    """
    Retrieve full invoice details with aggregate line items.
    """
    db = get_db(request)
    invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    items = await db.invoice_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    return {
        "invoice": invoice_doc,
        "items": items
    }

@invoice_router.post("/invoices/{invoice_id}/issue")
async def issue_invoice(
    request: Request,
    invoice_id: str,
    user: Dict = Depends(require_admin)
):
    """
    Transition invoice from draft to issued. Locks amounts and timestamps issued_at.
    """
    db = get_db(request)
    return await BillingService.issue_invoice(
        db, invoice_id, actor_user_id=user.get("user_id"), actor_name=user.get("name")
    )

@invoice_router.post("/invoices/{invoice_id}/pay")
async def mark_invoice_paid(
    request: Request,
    invoice_id: str,
    user: Dict = Depends(require_admin)
):
    """
    Mark issued invoice as paid.
    """
    db = get_db(request)
    return await BillingService.mark_invoice_paid(
        db, invoice_id, actor_user_id=user.get("user_id"), actor_name=user.get("name")
    )

@invoice_router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice(
    request: Request,
    invoice_id: str,
    payload: InvoiceCancelRequest = InvoiceCancelRequest(),
    user: Dict = Depends(require_admin)
):
    """
    Cancel an invoice and release linked bookings for potential re-invoicing.
    """
    db = get_db(request)
    return await BillingService.cancel_invoice(
        db, invoice_id, reason=payload.reason, actor_user_id=user.get("user_id"), actor_name=user.get("name")
    )

@invoice_router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    request: Request,
    invoice_id: str,
    user: Dict = Depends(require_admin)
):
    """
    Download aggregate corporate PDF invoice for FCA Admin.
    """
    db = get_db(request)
    invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    items_docs = await db.invoice_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    items = [InvoiceItem(**it) for it in items_docs]
    invoice = Invoice(**invoice_doc)
    org = await db.organisations.find_one({"id": invoice.organisation_id}, {"_id": 0})

    pdf_bytes = BillingService.generate_invoice_pdf(invoice, items, org)

    await AuditService.log_activity(
        db=db,
        action="invoice_downloaded",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={"invoice_id": invoice_id, "invoice_number": invoice.invoice_number, "caller": "admin"}
    )

    filename = f"FCA_Invoice_{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ==================== Corporate HR Portal Invoice Endpoints ====================

@invoice_router.get("/hr/invoices")
async def list_hr_invoices(
    request: Request,
    user: Dict = Depends(require_hr_user)
):
    """
    List issued/paid invoices strictly for the HR user's authenticated organisation.
    Draft and cancelled invoices are hidden from HR.
    """
    db = get_db(request)
    org_id = user.get("organisation_id")
    if not org_id and user.get("role") in ["super_admin", "admin"]:
        # Admin inspecting HR view
        org_id = request.query_params.get("organisation_id")

    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organisation ID required")

    # HR only sees issued and paid invoices
    docs = await db.invoices.find(
        {"organisation_id": org_id, "status": {"$in": ["issued", "paid"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    # Return safe representation with zero booking linkage
    safe_invoices = []
    for d in docs:
        safe_invoices.append({
            "id": d.get("id"),
            "invoice_number": d.get("invoice_number"),
            "organisation_name": d.get("organisation_name"),
            "billing_period_start": d.get("billing_period_start"),
            "billing_period_end": d.get("billing_period_end"),
            "currency": d.get("currency", "BWP"),
            "total_sessions": d.get("total_sessions"),
            "subtotal": d.get("subtotal"),
            "total": d.get("total"),
            "status": d.get("status"),
            "issued_at": d.get("issued_at"),
            "due_date": d.get("due_date"),
            "paid_at": d.get("paid_at")
        })

    return safe_invoices

@invoice_router.get("/hr/invoices/{invoice_id}/pdf")
async def download_hr_invoice_pdf(
    request: Request,
    invoice_id: str,
    user: Dict = Depends(require_hr_user)
):
    """
    Download aggregate corporate PDF invoice for an authenticated HR user.
    Enforces strict tenant isolation: HR can only download their own organisation's invoices.
    """
    db = get_db(request)
    org_id = user.get("organisation_id")

    invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Strict multi-tenant verification
    if user.get("role") in ["hr_admin", "hr_viewer"]:
        if invoice_doc.get("organisation_id") != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Cannot access invoices belonging to another organisation."
            )
        if invoice_doc.get("status") not in ["issued", "paid"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only issued or paid invoices are available."
            )

    items_docs = await db.invoice_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    items = [InvoiceItem(**it) for it in items_docs]
    invoice = Invoice(**invoice_doc)
    org = await db.organisations.find_one({"id": invoice.organisation_id}, {"_id": 0})

    pdf_bytes = BillingService.generate_invoice_pdf(invoice, items, org)

    await AuditService.log_activity(
        db=db,
        action="invoice_downloaded",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={"invoice_id": invoice_id, "invoice_number": invoice.invoice_number, "caller": "hr"}
    )

    filename = f"FCA_Corporate_Invoice_{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
