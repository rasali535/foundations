import React, { useState, useEffect } from 'react';
import { hrApi } from '../HRAuthContext';
import {
  Receipt,
  Download,
  Calendar,
  Building2,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';

const HRInvoices = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);

  const fetchInvoices = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await hrApi.get('/hr/invoices');
      setInvoices(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load corporate invoices.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleDownloadPdf = async (inv) => {
    setDownloadingId(inv.id);
    try {
      const res = await hrApi.get(`/hr/invoices/${inv.id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `FCA_Corporate_Invoice_${inv.invoice_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert('Failed to download invoice PDF.');
    } finally {
      setDownloadingId(null);
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'paid') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3 h-3" /> Paid
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
        <Clock className="w-3 h-3" /> Issued
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-black text-slate-900 flex items-center gap-2.5">
          <Receipt className="w-6 h-6 text-teal-700" />
          Corporate Invoices
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Review and download privacy-safe aggregate billing statements for your organisation.
        </p>
      </div>

      {/* Privacy Guarantee Box */}
      <div className="bg-teal-50/70 border border-teal-200/80 rounded-xl p-4 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed text-teal-900">
          <span className="font-bold">Strict Confidentiality Standard:</span> Corporate invoices are strictly aggregate statements.
          In accordance with psychological confidentiality standards, invoices do not include employee identities, appointment timestamps,
          or clinical case reasons.
        </div>
      </div>

      {/* Invoices List Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
            Issued Statements
          </h2>
          <button
            onClick={fetchInvoices}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh Invoices"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-teal-700" />
            <p className="text-xs font-medium">Loading corporate invoices...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600">
            <AlertCircle className="w-6 h-6 mx-auto mb-2" />
            <p className="text-xs font-medium">{error}</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <Receipt className="w-10 h-10 mx-auto text-slate-300" />
            <p className="text-sm font-bold text-slate-700">No Corporate Invoices Yet</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Issued billing statements will appear here once finalized by Foundations Counselling & Advisory.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3.5 font-bold">Invoice Number</th>
                  <th className="px-5 py-3.5 font-bold">Billing Period</th>
                  <th className="px-5 py-3.5 font-bold text-center">Sessions</th>
                  <th className="px-5 py-3.5 font-bold text-right">Invoice Total</th>
                  <th className="px-5 py-3.5 font-bold text-center">Status</th>
                  <th className="px-5 py-3.5 font-bold">Issue Date</th>
                  <th className="px-5 py-3.5 font-bold text-right">Download</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-5 py-4 font-bold text-slate-900 font-mono flex items-center gap-2">
                      <FileText className="w-4 h-4 text-teal-700" />
                      {inv.invoice_number}
                    </td>
                    <td className="px-5 py-4 font-mono text-slate-600 whitespace-nowrap">
                      {inv.billing_period_start} → {inv.billing_period_end}
                    </td>
                    <td className="px-5 py-4 text-center font-bold text-slate-800">
                      {inv.total_sessions}
                    </td>
                    <td className="px-5 py-4 text-right font-black text-slate-900 whitespace-nowrap">
                      {inv.currency} {inv.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-5 py-4 text-center">
                      {getStatusBadge(inv.status)}
                    </td>
                    <td className="px-5 py-4 text-slate-500 whitespace-nowrap">
                      {inv.issued_at ? inv.issued_at.slice(0, 10) : '—'}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => handleDownloadPdf(inv)}
                        disabled={downloadingId === inv.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-700 hover:bg-teal-800 disabled:bg-teal-300 text-white rounded-lg shadow-sm font-medium transition-colors"
                      >
                        {downloadingId === inv.id ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default HRInvoices;
