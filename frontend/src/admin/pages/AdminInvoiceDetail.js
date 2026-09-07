import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  Receipt,
  ArrowLeft,
  Calendar,
  Building2,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Download,
  ShieldCheck,
  Ban,
  Check,
  RefreshCw
} from 'lucide-react';

const AdminInvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Actions state
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Cancellation Modal
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const fetchInvoiceDetail = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/invoices/${id}`);
      setInvoice(res.data.invoice);
      setItems(res.data.items);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load invoice details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchInvoiceDetail();
  }, [fetchInvoiceDetail]);

  const handleIssue = async () => {
    if (!window.confirm('Are you sure you want to issue this invoice? Issued invoices are historically locked accounting records.')) {
      return;
    }
    setActionLoading(true);
    setActionError('');
    try {
      await api.post(`/invoices/${id}/issue`);
      await fetchInvoiceDetail();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to issue invoice.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkPaid = async () => {
    if (!window.confirm('Mark this invoice as paid?')) return;
    setActionLoading(true);
    setActionError('');
    try {
      await api.post(`/invoices/${id}/pay`);
      await fetchInvoiceDetail();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to mark invoice paid.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    setActionLoading(true);
    setActionError('');
    try {
      await api.post(`/invoices/${id}/cancel`, { reason: cancelReason || 'Cancelled by admin' });
      setCancelModalOpen(false);
      setCancelReason('');
      await fetchInvoiceDetail();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to cancel invoice.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const res = await api.get(`/invoices/${id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `FCA_Invoice_${invoice?.invoice_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert('Failed to download invoice PDF.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'paid':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> Paid
          </span>
        );
      case 'issued':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <Clock className="w-3.5 h-3.5" /> Issued
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <FileText className="w-3.5 h-3.5" /> Draft
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5" /> Cancelled
          </span>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
        <p className="text-sm font-medium">Loading invoice record...</p>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="p-8 bg-white rounded-xl border border-rose-200 text-center text-rose-700 space-y-3">
          <AlertCircle className="w-8 h-8 mx-auto text-rose-600" />
          <p className="font-semibold">{error || 'Invoice record not found.'}</p>
          <button
            onClick={() => navigate('/admin/invoices')}
            className="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-lg"
          >
            Back to Invoices
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Top Bar with Back Link & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/invoices')}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            title="Back to Invoices"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-900 font-mono">
                {invoice.invoice_number}
              </h1>
              {getStatusBadge(invoice.status)}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Created on {invoice.created_at ? invoice.created_at.slice(0, 10) : '—'}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {invoice.status === 'draft' && (
            <>
              <button
                onClick={handleIssue}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg shadow transition-colors"
              >
                <Check className="w-4 h-4" />
                Issue Invoice
              </button>
              <button
                onClick={() => setCancelModalOpen(true)}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-3 py-2 border border-slate-200 hover:bg-slate-50 text-rose-600 text-sm font-medium rounded-lg transition-colors"
              >
                <Ban className="w-4 h-4" />
                Cancel
              </button>
            </>
          )}

          {invoice.status === 'issued' && (
            <>
              <button
                onClick={handleMarkPaid}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm font-medium rounded-lg shadow transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                Mark as Paid
              </button>
              <button
                onClick={() => setCancelModalOpen(true)}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-3 py-2 border border-slate-200 hover:bg-slate-50 text-rose-600 text-sm font-medium rounded-lg transition-colors"
              >
                <Ban className="w-4 h-4" />
                Cancel
              </button>
            </>
          )}

          {/* PDF Download Button Available on all states */}
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white text-sm font-medium rounded-lg shadow transition-colors"
          >
            {downloadingPdf ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Download PDF
          </button>
        </div>
      </div>

      {actionError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Invoice Overview Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Billed Organisation</p>
            <p className="text-base font-bold text-slate-900 mt-1 flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-emerald-600 shrink-0" />
              {invoice.organisation_name}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Billing Period</p>
            <p className="text-sm font-medium text-slate-800 mt-1 font-mono">
              {invoice.billing_period_start} to {invoice.billing_period_end}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Issue / Paid Dates</p>
            <p className="text-sm text-slate-700 mt-1">
              Issued: {invoice.issued_at ? invoice.issued_at.slice(0, 10) : 'Not issued'}<br />
              {invoice.paid_at && <span className="text-emerald-700 font-semibold">Paid: {invoice.paid_at.slice(0, 10)}</span>}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Payment Total</p>
            <p className="text-xl font-black text-slate-900 mt-1">
              {invoice.currency} {invoice.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {invoice.status === 'cancelled' && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
            <p className="font-bold flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" /> Invoice Cancelled
            </p>
            <p>Reason: {invoice.cancellation_reason || 'No reason specified'}</p>
            <p className="text-slate-500">Linked bookings have been released and may be re-invoiced in future periods.</p>
          </div>
        )}

        {/* Aggregate Items Table */}
        <div>
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
            Aggregate Billing Line Items
          </h2>
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Description</th>
                  <th className="px-5 py-3 text-center">Session Type</th>
                  <th className="px-5 py-3 text-center">Completed Sessions</th>
                  <th className="px-5 py-3 text-right">Unit Rate ({invoice.currency})</th>
                  <th className="px-5 py-3 text-right">Line Total ({invoice.currency})</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((it) => (
                  <tr key={it.id}>
                    <td className="px-5 py-3.5 font-medium text-slate-900">
                      {it.description}
                    </td>
                    <td className="px-5 py-3.5 text-center capitalize text-slate-600">
                      {it.session_type}
                    </td>
                    <td className="px-5 py-3.5 text-center font-bold text-slate-800">
                      {it.quantity}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-slate-700">
                      {it.unit_price.toFixed(2)}
                    </td>
                    <td className="px-5 py-3.5 text-right font-bold font-mono text-slate-900">
                      {it.line_total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 font-bold border-t border-slate-200 text-slate-900">
                <tr>
                  <td colSpan="2" className="px-5 py-3.5 text-right uppercase text-xs tracking-wider">
                    Total Completed Sessions & Final Amount
                  </td>
                  <td className="px-5 py-3.5 text-center font-black text-emerald-700">
                    {invoice.total_sessions}
                  </td>
                  <td></td>
                  <td className="px-5 py-3.5 text-right text-base text-emerald-700">
                    {invoice.currency} {invoice.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Privacy Box */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-start gap-2.5">
          <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-slate-800">Privacy & Confidentiality Standard</p>
            <p className="mt-0.5 text-slate-500">
              This invoice is an aggregate corporate statement. Individual client names, employee numbers, booking timestamps, clinical reasons, and therapist relationships are strictly excluded to preserve client privacy.
            </p>
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      {cancelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 text-rose-700">
              <AlertCircle className="w-5 h-5" /> Cancel Invoice {invoice.invoice_number}
            </h3>
            <p className="text-sm text-slate-600">
              Cancelling this invoice will preserve the invoice number in the audit record and release all {invoice.total_sessions} linked session(s) back into the uninvoiced pool.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Cancellation Reason
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g., Billing period correction, contract adjustment..."
                rows="3"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalOpen(false)}
                disabled={actionLoading}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-lg"
              >
                Keep Invoice
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={actionLoading}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-lg shadow"
              >
                {actionLoading ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminInvoiceDetail;
