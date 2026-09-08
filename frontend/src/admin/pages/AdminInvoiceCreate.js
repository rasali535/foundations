import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  Receipt,
  ArrowLeft,
  Calendar,
  Building2,
  AlertCircle,
  CheckCircle2,
  FileText,
  Calculator,
  RefreshCw
} from 'lucide-react';

const AdminInvoiceCreate = () => {
  const navigate = useNavigate();
  const [organisations, setOrganisations] = useState([]);
  const [loadingOrgs, setLoadingOrgs] = useState(true);

  // Form State
  const [organisationId, setOrganisationId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [dueDate, setDueDate] = useState('');

  // Preview State
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewError, setPreviewError] = useState('');

  // Generation State
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const res = await api.get('/admin-ops/organisations');
        setOrganisations(res.data);
      } catch (err) {
        console.error('Failed to load organisations:', err);
      } finally {
        setLoadingOrgs(false);
      }
    };
    fetchOrgs();

    // Default dates: current month
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const lastDay = new Date(year, now.getMonth() + 1, 0).getDate();
    setStartDate(`${year}-${month}-01`);
    setEndDate(`${year}-${month}-${String(lastDay).padStart(2, '0')}`);
  }, []);

  const handlePreview = async () => {
    if (!organisationId || !startDate || !endDate) {
      setPreviewError('Please select an organisation and valid date range.');
      return;
    }
    setPreviewError('');
    setPreviewLoading(true);
    setPreviewData(null);
    try {
      const res = await api.get('/invoices/preview', {
        params: {
          organisation_id: organisationId,
          billing_period_start: startDate,
          billing_period_end: endDate
        }
      });
      setPreviewData(res.data);
    } catch (err) {
      setPreviewError(err.response?.data?.detail || 'Failed to preview invoice.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerateInvoice = async () => {
    if (!organisationId || !startDate || !endDate) return;
    setCreating(true);
    setCreateError('');
    try {
      const payload = {
        organisation_id: organisationId,
        billing_period_start: startDate,
        billing_period_end: endDate,
        due_date: dueDate || undefined
      };
      const res = await api.post('/invoices', payload);
      const newInvoice = res.data.invoice;
      navigate(`/admin/invoices/${newInvoice.id}`);
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to generate draft invoice.');
      setCreating(false);
    }
  };

  const selectedOrgObj = organisations.find(o => o.id === organisationId);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Back link & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/admin/invoices')}
          className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Receipt className="w-6 h-6 text-emerald-600" />
            Generate Corporate Invoice
          </h1>
          <p className="text-sm text-slate-600">
            Preview and generate an aggregate invoice from completed sessions and billable late cancellations.
          </p>
        </div>
      </div>

      {/* Scope Parameters Form */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
        <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-emerald-600" />
          1. Billing Scope & Target Organisation
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Target Organisation *
            </label>
            <select
              value={organisationId}
              onChange={(e) => {
                setOrganisationId(e.target.value);
                setPreviewData(null);
              }}
              disabled={loadingOrgs}
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">-- Select Corporate Organisation --</option>
              {organisations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name} ({org.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Billing Period Start *
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setPreviewData(null);
              }}
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Billing Period End *
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setPreviewData(null);
              }}
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Payment Due Date (Optional)
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full sm:w-1/2 px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            onClick={handlePreview}
            disabled={previewLoading || !organisationId || !startDate || !endDate}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            {previewLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Scanning Bookings...
              </>
            ) : (
              <>
                <Calculator className="w-4 h-4" />
                Preview Billable Sessions
              </>
            )}
          </button>
        </div>
      </div>

      {previewError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm flex items-start gap-2.5">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Unable to Preview Invoice</p>
            <p className="text-rose-700 mt-0.5">{previewError}</p>
          </div>
        </div>
      )}

      {/* Live Preview Section */}
      {previewData && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                2. Billable Sessions Preview
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Eligible uninvoiced billable sessions (completed &amp; late-cancelled) for <span className="font-semibold text-slate-800">{previewData.organisation_name}</span>.
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Billable</span>
              <p className="text-xl font-bold text-slate-900">
                {previewData.currency} {previewData.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
          </div>

          {previewData.total_sessions === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 text-slate-600">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
              <p className="font-semibold text-slate-800">No Uninvoiced Billable Sessions Found</p>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                There are no completed or late-cancelled bookings for this organisation within the selected date range that have not already been billed.
              </p>
            </div>
          ) : (
            <>
              {/* Itemized Table */}
              <div className="overflow-x-auto border border-slate-100 rounded-lg">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3 text-center">Session Type</th>
                      <th className="px-4 py-3 text-center">Quantity</th>
                      <th className="px-4 py-3 text-right">Fixed Rate</th>
                      <th className="px-4 py-3 text-right">Line Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {previewData.items.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3 font-medium text-slate-900">
                          {item.description}
                        </td>
                        <td className="px-4 py-3 text-center capitalize text-slate-600">
                          {item.session_type}
                        </td>
                        <td className="px-4 py-3 text-center font-bold text-slate-800">
                          {item.quantity}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-slate-700">
                          BWP {item.unit_price.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold font-mono text-slate-900">
                          BWP {item.line_total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50 font-bold border-t border-slate-200 text-slate-900">
                    <tr>
                      <td colSpan="2" className="px-4 py-3 text-right uppercase text-xs tracking-wider">
                        Total Sessions & Estimated Amount
                      </td>
                      <td className="px-4 py-3 text-center font-black text-emerald-700">
                        {previewData.total_sessions}
                      </td>
                      <td></td>
                      <td className="px-4 py-3 text-right text-base text-emerald-700">
                        BWP {previewData.total.toLocaleString('en-BW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Double-billing & Privacy notice */}
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <p>
                  <b>Double-Billing Guard Active:</b> Generating this invoice will atomically link these {previewData.total_sessions} session(s) to the draft invoice, preventing duplicate billing in future runs.
                </p>
              </div>

              {createError && (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              {/* Action Button */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  Initial status will be set to <span className="font-semibold text-amber-700">draft</span> for inspection before issuing.
                </p>
                <button
                  type="button"
                  onClick={handleGenerateInvoice}
                  disabled={creating}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-medium rounded-lg shadow transition-colors"
                >
                  {creating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Creating Invoice...
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4" />
                      Generate Draft Invoice
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminInvoiceCreate;
