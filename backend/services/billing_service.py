from datetime import datetime, timezone
from decimal import Decimal
import io
import logging
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import (
    now_iso,
    Invoice,
    InvoiceItem,
    InvoiceBookingLink,
    InvoicePreviewItem,
    InvoicePreviewResponse,
    SESSION_RATES,
    SESSION_TYPE_DESCRIPTIONS,
    DEFAULT_CURRENCY
)
from services.audit_service import AuditService

# ReportLab imports for safe PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

class BillingService:
    @staticmethod
    async def get_next_invoice_number(db: AsyncIOMotorDatabase, year: Optional[int] = None) -> str:
        """
        Generate atomic sequential invoice number in format FCA-INV-YYYY-0001
        Uses system_counters with concurrency protection.
        """
        if year is None:
            year = datetime.now(timezone.utc).year
        counter_id = f"invoice_number_seq_{year}"
        try:
            counter = await db.system_counters.find_one_and_update(
                {"_id": counter_id},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True
            )
            seq = counter.get("seq", 1) if counter else 1
            return f"FCA-INV-{year}-{seq:04d}"
        except Exception as e:
            logging.warning(f"Counter increment fallback for invoice number: {e}")
            count = await db.invoices.count_documents({"invoice_number": {"$regex": f"^FCA-INV-{year}-"}})
            return f"FCA-INV-{year}-{count + 1:04d}"

    @staticmethod
    async def get_uninvoiced_completed_sessions(
        db: AsyncIOMotorDatabase,
        organisation_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Find billable, uninvoiced sessions for an organisation within a date range.
        Mandatory rules:
        1. Client must belong to organisation_id
        2. status in ['completed', 'late_cancelled_billable']
        3. starts_at falls within [start_date, end_date]
        4. Exclude any booking already linked to an active (non-cancelled) invoice
        """
        # Find all client IDs for this organisation
        client_docs = await db.crm_clients.find(
            {"organisation_id": organisation_id},
            {"id": 1, "_id": 0}
        ).to_list(10000)
        
        client_ids = [c["id"] for c in client_docs if "id" in c]
        if not client_ids:
            return []

        # Find all booking IDs already attached to an active invoice (draft, issued, paid)
        active_invoices = await db.invoices.find(
            {"organisation_id": organisation_id, "status": {"$in": ["draft", "issued", "paid"]}},
            {"id": 1, "_id": 0}
        ).to_list(10000)
        active_invoice_ids = [inv["id"] for inv in active_invoices if "id" in inv]

        linked_booking_docs = []
        if active_invoice_ids:
            linked_booking_docs = await db.invoice_booking_links.find(
                {"invoice_id": {"$in": active_invoice_ids}},
                {"booking_id": 1, "_id": 0}
            ).to_list(50000)
        already_invoiced_booking_ids = set(l["booking_id"] for l in linked_booking_docs if "booking_id" in l)

        # Query completed or late_cancelled_billable bookings for these clients
        booking_cursor = db.bookings.find({
            "client_id": {"$in": client_ids},
            "status": {"$in": ["completed", "late_cancelled_billable"]}
        })
        all_completed = await booking_cursor.to_list(20000)

        eligible_bookings = []
        for b in all_completed:
            # Check date range using ISO date prefix YYYY-MM-DD
            starts_at = b.get("starts_at", "")
            date_str = starts_at[:10] if len(starts_at) >= 10 else ""
            if not date_str:
                continue
            if date_str < start_date or date_str > end_date:
                continue
            
            # Double-billing check: must not be in already_invoiced_booking_ids
            bid = b.get("id")
            if bid in already_invoiced_booking_ids:
                continue
            # Also check direct active_invoice_id if set
            if b.get("active_invoice_id") and b.get("active_invoice_id") in active_invoice_ids:
                continue

            eligible_bookings.append(b)

        return eligible_bookings

    @staticmethod
    def calculate_totals(session_counts: Dict[str, int]) -> Tuple[List[InvoicePreviewItem], Decimal, Decimal, int]:
        """
        Deterministic, Decimal/currency-safe arithmetic calculation of line items and totals.
        No floating-point rounding errors.
        """
        items: List[InvoicePreviewItem] = []
        subtotal = Decimal("0.00")
        total_sessions = 0

        # Always evaluate standard session types
        for s_type in ["individual", "couple", "family"]:
            qty = session_counts.get(s_type, 0)
            if qty > 0:
                rate = SESSION_RATES.get(s_type, Decimal("0.00"))
                line_total = Decimal(qty) * rate
                subtotal += line_total
                total_sessions += qty
                items.append(InvoicePreviewItem(
                    session_type=s_type,
                    description=SESSION_TYPE_DESCRIPTIONS.get(s_type, f"{s_type.capitalize()} Counselling"),
                    quantity=qty,
                    unit_price=float(rate),
                    line_total=float(line_total)
                ))

        # Check any other custom session types if present
        for s_type, qty in session_counts.items():
            if s_type not in ["individual", "couple", "family"] and qty > 0:
                rate = SESSION_RATES.get(s_type, Decimal("350.00"))
                line_total = Decimal(qty) * rate
                subtotal += line_total
                total_sessions += qty
                items.append(InvoicePreviewItem(
                    session_type=s_type,
                    description=SESSION_TYPE_DESCRIPTIONS.get(s_type, f"{s_type.capitalize()} Counselling"),
                    quantity=qty,
                    unit_price=float(rate),
                    line_total=float(line_total)
                ))

        total = subtotal
        return items, subtotal, total, total_sessions

    @staticmethod
    async def preview_invoice(
        db: AsyncIOMotorDatabase,
        organisation_id: str,
        start_date: str,
        end_date: str
    ) -> InvoicePreviewResponse:
        """
        Generate live preview of completed uninvoiced sessions without modifying the database.
        """
        org = await db.organisations.find_one({"id": organisation_id})
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

        eligible_sessions = await BillingService.get_uninvoiced_completed_sessions(
            db, organisation_id, start_date, end_date
        )

        counts: Dict[str, int] = {}
        for s in eligible_sessions:
            stype = str(s.get("session_type", "individual")).lower().strip()
            counts[stype] = counts.get(stype, 0) + 1

        items, subtotal, total, total_sessions = BillingService.calculate_totals(counts)

        return InvoicePreviewResponse(
            organisation_id=organisation_id,
            organisation_name=org.get("name", "Unknown Organisation"),
            billing_period_start=start_date,
            billing_period_end=end_date,
            currency=DEFAULT_CURRENCY,
            items=items,
            total_sessions=total_sessions,
            subtotal=float(subtotal),
            total=float(total)
        )

    @staticmethod
    async def create_draft_invoice(
        db: AsyncIOMotorDatabase,
        organisation_id: str,
        start_date: str,
        end_date: str,
        due_date: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[Invoice, List[InvoiceItem]]:
        """
        Create a new draft invoice linked to completed sessions.
        Atomically establishes invoice_booking_links and locks bookings from double-billing.
        """
        org = await db.organisations.find_one({"id": organisation_id})
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

        eligible_sessions = await BillingService.get_uninvoiced_completed_sessions(
            db, organisation_id, start_date, end_date
        )
        if not eligible_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eligible completed uninvoiced sessions found for this organisation and billing period."
            )

        counts: Dict[str, int] = {}
        for s in eligible_sessions:
            stype = str(s.get("session_type", "individual")).lower().strip()
            counts[stype] = counts.get(stype, 0) + 1

        items_preview, subtotal, total, total_sessions = BillingService.calculate_totals(counts)

        year = int(start_date[:4]) if len(start_date) >= 4 and start_date[:4].isdigit() else datetime.now(timezone.utc).year
        invoice_number = await BillingService.get_next_invoice_number(db, year)

        invoice = Invoice(
            invoice_number=invoice_number,
            organisation_id=organisation_id,
            organisation_name=org.get("name", "Corporate Client"),
            billing_period_start=start_date,
            billing_period_end=end_date,
            currency=DEFAULT_CURRENCY,
            subtotal=float(subtotal),
            total=float(total),
            total_sessions=total_sessions,
            status="draft",
            due_date=due_date,
            created_by=actor_user_id,
            created_at=now_iso(),
            updated_at=now_iso()
        )

        # Create Invoice Items
        invoice_items: List[InvoiceItem] = []
        for prev in items_preview:
            item = InvoiceItem(
                invoice_id=invoice.id,
                session_type=prev.session_type,
                description=prev.description,
                quantity=prev.quantity,
                unit_price=prev.unit_price,
                line_total=prev.line_total,
                created_at=now_iso()
            )
            invoice_items.append(item)

        # Create Booking Links
        booking_links: List[InvoiceBookingLink] = []
        booking_ids: List[str] = []
        for b in eligible_sessions:
            bid = b.get("id")
            booking_ids.append(bid)
            booking_links.append(InvoiceBookingLink(
                invoice_id=invoice.id,
                booking_id=bid,
                session_type=str(b.get("session_type", "individual")),
                starts_at=b.get("starts_at"),
                created_at=now_iso()
            ))

        # Atomic persistence
        await db.invoices.insert_one(invoice.model_dump())
        if invoice_items:
            await db.invoice_items.insert_many([it.model_dump() for it in invoice_items])
        if booking_links:
            await db.invoice_booking_links.insert_many([bl.model_dump() for bl in booking_links])

        # Mark active_invoice_id on bookings
        if booking_ids:
            await db.bookings.update_many(
                {"id": {"$in": booking_ids}},
                {"$set": {"active_invoice_id": invoice.id, "updated_at": now_iso()}}
            )

        # Audit log
        await AuditService.log_activity(
            db=db,
            action="invoice_created",
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            metadata={
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "organisation_id": organisation_id,
                "total_sessions": total_sessions,
                "total_amount": float(total)
            }
        )

        return invoice, invoice_items

    @staticmethod
    async def issue_invoice(
        db: AsyncIOMotorDatabase,
        invoice_id: str,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Invoice:
        """
        Transition invoice from draft -> issued.
        Sets issued_at timestamp and locks financial record.
        """
        invoice_doc = await db.invoices.find_one({"id": invoice_id})
        if not invoice_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        if invoice_doc.get("status") != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot issue invoice with status '{invoice_doc.get('status')}'. Must be draft."
            )

        now = now_iso()
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "issued", "issued_at": now, "updated_at": now}}
        )

        updated_doc = await db.invoices.find_one({"id": invoice_id})
        updated_invoice = Invoice(**updated_doc)

        await AuditService.log_activity(
            db=db,
            action="invoice_issued",
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            metadata={
                "invoice_id": invoice_id,
                "invoice_number": updated_invoice.invoice_number,
                "organisation_id": updated_invoice.organisation_id,
                "issued_at": now
            }
        )

        return updated_invoice

    @staticmethod
    async def mark_invoice_paid(
        db: AsyncIOMotorDatabase,
        invoice_id: str,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Invoice:
        """
        Transition invoice from issued -> paid.
        Stores paid_at timestamp.
        """
        invoice_doc = await db.invoices.find_one({"id": invoice_id})
        if not invoice_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        if invoice_doc.get("status") != "issued":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark invoice as paid with status '{invoice_doc.get('status')}'. Must be issued."
            )

        now = now_iso()
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "paid", "paid_at": now, "updated_at": now}}
        )

        updated_doc = await db.invoices.find_one({"id": invoice_id})
        updated_invoice = Invoice(**updated_doc)

        await AuditService.log_activity(
            db=db,
            action="invoice_marked_paid",
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            metadata={
                "invoice_id": invoice_id,
                "invoice_number": updated_invoice.invoice_number,
                "organisation_id": updated_invoice.organisation_id,
                "paid_at": now
            }
        )

        return updated_invoice

    @staticmethod
    async def cancel_invoice(
        db: AsyncIOMotorDatabase,
        invoice_id: str,
        reason: Optional[str] = "Cancelled by admin",
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Invoice:
        """
        Cancels an invoice, preserves historical invoice record, and releases
        linked bookings so they can be re-invoiced if needed.
        """
        invoice_doc = await db.invoices.find_one({"id": invoice_id})
        if not invoice_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        if invoice_doc.get("status") == "cancelled":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice is already cancelled.")

        now = now_iso()
        # Find all linked bookings
        links = await db.invoice_booking_links.find({"invoice_id": invoice_id}).to_list(10000)
        booking_ids = [l["booking_id"] for l in links if "booking_id" in l]

        # Release active_invoice_id from bookings
        if booking_ids:
            await db.bookings.update_many(
                {"id": {"$in": booking_ids}, "active_invoice_id": invoice_id},
                {"$set": {"active_invoice_id": None, "updated_at": now}}
            )

        # Update invoice status to cancelled
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "cancellation_reason": reason,
                "updated_at": now
            }}
        )

        updated_doc = await db.invoices.find_one({"id": invoice_id})
        updated_invoice = Invoice(**updated_doc)

        await AuditService.log_activity(
            db=db,
            action="invoice_cancelled",
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            metadata={
                "invoice_id": invoice_id,
                "invoice_number": updated_invoice.invoice_number,
                "organisation_id": updated_invoice.organisation_id,
                "cancellation_reason": reason,
                "released_bookings_count": len(booking_ids)
            }
        )

        return updated_invoice

    @staticmethod
    def generate_invoice_pdf(
        invoice: Invoice,
        items: List[InvoiceItem],
        organisation: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate a professional, privacy-preserving PDF invoice using ReportLab.
        STRICT COMPLIANCE:
        - Only aggregate line items (quantity, unit rate, line total)
        - Bill to: Organisation name
        - ZERO client names, emails, phone numbers, CRM IDs, or clinical information
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        
        # Define bespoke styles
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a")
        )
        subtitle_style = ParagraphStyle(
            'InvoiceSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b")
        )
        badge_style = ParagraphStyle(
            'StatusBadge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#0f766e") if invoice.status in ["issued", "paid"] else colors.HexColor("#b45309")
        )
        meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569")
        )
        meta_value_style = ParagraphStyle(
            'MetaValue',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#0f172a")
        )
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#ffffff")
        )
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1e293b")
        )
        table_cell_right_style = ParagraphStyle(
            'TableCellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#1e293b")
        )
        table_total_style = ParagraphStyle(
            'TableTotal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#0f172a")
        )
        privacy_note_style = ParagraphStyle(
            'PrivacyNote',
            parent=styles['Italic'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER
        )

        elements = []

        # Header Block
        header_table_data = [
            [
                Paragraph("FOUNDATIONS COUNSELLING & ADVISORY", title_style),
                Paragraph(f"INVOICE<br/><b>{invoice.invoice_number}</b>", ParagraphStyle(
                    'InvNum', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=TA_RIGHT, textColor=colors.HexColor("#0f766e")
                ))
            ],
            [
                Paragraph("Specialist Psychological & Corporate Well-being Services", subtitle_style),
                Paragraph(f"Status: <b>{invoice.status.upper()}</b>", badge_style)
            ]
        ]
        header_table = Table(header_table_data, colWidths=[340, 190])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

        # Bill To & Meta Section
        org_name = invoice.organisation_name
        bill_to_text = f"<b>Bill To:</b><br/>{org_name}"
        if organisation and organisation.get("contact_person"):
            bill_to_text += f"<br/>Attn: {organisation.get('contact_person')}"

        meta_right_data = [
            [Paragraph("Issue Date:", meta_label_style), Paragraph(invoice.issued_at[:10] if invoice.issued_at else invoice.created_at[:10], meta_value_style)],
            [Paragraph("Billing Period:", meta_label_style), Paragraph(f"{invoice.billing_period_start} to {invoice.billing_period_end}", meta_value_style)],
            [Paragraph("Payment Currency:", meta_label_style), Paragraph(invoice.currency, meta_value_style)],
        ]
        if invoice.due_date:
            meta_right_data.append([Paragraph("Due Date:", meta_label_style), Paragraph(invoice.due_date, meta_value_style)])
        if invoice.paid_at:
            meta_right_data.append([Paragraph("Paid Date:", meta_label_style), Paragraph(invoice.paid_at[:10], meta_value_style)])

        meta_right_table = Table(meta_right_data, colWidths=[90, 140])
        meta_right_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))

        info_table_data = [
            [Paragraph(bill_to_text, meta_value_style), meta_right_table]
        ]
        info_table = Table(info_table_data, colWidths=[300, 230])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 25))

        # Items Table
        table_rows = [
            [
                Paragraph("Description", table_header_style),
                Paragraph("Session Type", table_header_style),
                Paragraph("Quantity", ParagraphStyle('HRight1', parent=table_header_style, alignment=TA_RIGHT)),
                Paragraph("Rate (BWP)", ParagraphStyle('HRight2', parent=table_header_style, alignment=TA_RIGHT)),
                Paragraph("Line Total (BWP)", ParagraphStyle('HRight3', parent=table_header_style, alignment=TA_RIGHT)),
            ]
        ]

        for item in items:
            table_rows.append([
                Paragraph(item.description, table_cell_style),
                Paragraph(item.session_type.capitalize(), table_cell_style),
                Paragraph(str(item.quantity), table_cell_right_style),
                Paragraph(f"{item.unit_price:,.2f}", table_cell_right_style),
                Paragraph(f"{item.line_total:,.2f}", table_cell_right_style)
            ])

        # Summary Rows
        table_rows.append([
            "",
            "",
            Paragraph(f"<b>{invoice.total_sessions}</b>", table_cell_right_style),
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(f"<b>BWP {invoice.total:,.2f}</b>", table_total_style)
        ])

        col_widths = [190, 110, 65, 80, 85]
        items_table = Table(table_rows, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#0f766e")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f8fafc")),
        ]))
        elements.append(items_table)

        elements.append(Spacer(1, 35))

        # Bottom Privacy & Compliance Statement
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=12))
        elements.append(Paragraph(
            "Confidential Corporate Billing Record — Aggregate Service Statement.<br/>"
            "In strict compliance with psychological data protection standards and client confidentiality protocols, "
            "individual client names, employee numbers, appointment times, and clinical case details are strictly excluded from all billing statements.",
            privacy_note_style
        ))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
