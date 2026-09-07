import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  Receipt,
  Plus,
  Search,
  Filter,
  Download,
  Calendar,
  Building2,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  ChevronRight,
  RefreshCw
} from 'lucide-react';

const AdminInvoices = () => {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [organisations, setOrganisations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedOrg, setSelectedOrg] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchOrganisations = async () => {
    try {
      const res = await api.get('/admin-ops/organisations');
      setOrganisations(res.data);
    } catch (err) {
      console.error('Error fetching organisations:', err);
    }
  };

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (selectedOrg) params.organisation_id = selectedOrg;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await api.get('/invoices', { params });
      setInvoices(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load invoices.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, selectedOrg, searchQuery]);

  useEffect(() => {
    fetchOrganisations();
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const handleDownloadPdf = async (invoice, e) => {
    e.stopPropagation();
    setDownloadingId(invoice.id);
    try {
      const res = await api.get(`/invoices/${invoice.id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `FCA_Invoice_${invoice.invoice_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert('Failed to download invoice PDF.');
    } finally {
      setDownloadingId(null);
    }
  };

  // KPI Calculations
  const totalBilled = invoices
    .filter(i => i.status !== 'cancelled')
    .reduce((acc, curr) => acc + (curr.total || 0), 0);
  const paidCount = invoices.filter(i => i.status === 'paid').length;
  const issuedCount = invoices.filter(i => i.status === 'issued').length;
  const draftCount = invoices.filter(i => i.status === 'draft').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'paid':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> Paid
          </span>
        );
      case 'issued':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <Clock className="w-3 h-3" /> Issued
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <FileText className="w-3 h-3" /> Draft
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <AlertCircle className="w-3 h-3" /> Cancelled
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Receipt className="w-7 h-7 text-emerald-600" />
            Corporate Invoices
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Session-based corporate billing for completed counselling services.
          </p>
        </div>
        <button
          onClick={() => navigate('/admin/invoices/new')}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow transition-colors"
        >
          <Plus className="w-4 h-4" />
          Generate Invoice
        </button>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Billing Volume</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">BWP {totalBilled.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          <p className="text-xs text-slate-400 mt-1">Excludes cancelled invoices</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Paid Invoices</p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">{paidCount}</p>
          <p className="text-xs text-slate-400 mt-1">Settled payments</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Issued / Pending</p>
          <p className="text-2xl font-bold text-blue-700 mt-1">{issuedCount}</p>
          <p className="text-xs text-slate-400 mt-1">Delivered to client</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Drafts</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{draftCount}</p>
          <p className="text-xs text-slate-400 mt-1">Awaiting admin issue</p>
        </div>
      </div>

      {/* Filters & Controls */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-4">
        {/* Status Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
          {['all', 'draft', 'issued', 'paid', 'cancelled'].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === tab
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Search & Org Filter */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search invoice number or organisation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div className="sm:w-64">
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            >
              <option value="">All Organisations</option>
              {organisations.map((org) => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={fetchInvoices}
            className="p-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refresh Invoices"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
            <p className="text-sm font-medium">Loading corporate invoices...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600">
            <AlertCircle className="w-6 h-6 mx-auto mb-2" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Receipt className="w-10 h-10 mx-auto mb-3 text-slate-300" />
            <p className="text-base font-semibold text-slate-700">No invoices found</p>
            <p className="text-sm text-slate-500 mt-1">
              Generate an invoice from completed counselling sessions to get started.
            </p>
            <button
              onClick={() => navigate('/admin/invoices/new')}
              className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow transition-colors"
            >
              Generate First Invoice
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Invoice Number</th>
                  <th className="px-5 py-3">Organisation</th>
                  <th className="px-5 py-3">Billing Period</th>
                  <th className="px-5 py-3 text-center">Sessions</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3">Date Issued</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => navigate(`/admin/invoices/${inv.id}`)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-4 font-semibold text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-emerald-600" />
                      {inv.invoice_number}
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-800">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        {inv.organisation_name}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-600 whitespace-nowrap">
                      <span className="text-xs text-slate-500 font-mono">
                        {inv.billing_period_start} → {inv.billing_period_end}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-center font-semibold text-slate-800">
                      {inv.total_sessions}
                    </td>
                    <td className="px-5 py-4 text-right font-bold text-slate-900 whitespace-nowrap">
                      {inv.currency} {inv.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-5 py-4 text-center">
                      {getStatusBadge(inv.status)}
                    </td>
                    <td className="px-5 py-4 text-slate-500 text-xs whitespace-nowrap">
                      {inv.issued_at ? inv.issued_at.slice(0, 10) : <span className="italic text-slate-400">—</span>}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={(e) => handleDownloadPdf(inv, e)}
                          disabled={downloadingId === inv.id}
                          className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                          title="Download PDF"
                        >
                          {downloadingId === inv.id ? (
                            <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
                          ) : (
                            <Download className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => navigate(`/admin/invoices/${inv.id}`)}
                          className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors"
                          title="View Details"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
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

export default AdminInvoices;
