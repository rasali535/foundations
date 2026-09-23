import React, { useCallback, useEffect, useState } from 'react';
import {
  ReceiptText,
  ShieldCheck,
  RefreshCw,
  CalendarDays,
  CircleDollarSign,
  FileCheck2,
  AlertCircle
} from 'lucide-react';
import { hrApi, useHRAuth } from '../HRAuthContext';

const periodOptions = [
  { key: 'current_month', label: 'Current Month' },
  { key: 'previous_month', label: 'Last Month' },
  { key: 'quarter', label: 'This Quarter' },
  { key: 'year', label: 'This Year' },
  { key: 'all_time', label: 'All Time' }
];

const labelize = (value) =>
  String(value || '').replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());

const HRBookingLedger = () => {
  const { user } = useHRAuth();
  const [period, setPeriod] = useState('current_month');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchLedger = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await hrApi.get(`/hr/booking-ledger?period=${period}`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load the accounts booking ledger.');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  if (user?.role === 'hr_viewer') {
    return (
      <div className="p-6 bg-amber-50 border border-amber-200 rounded-2xl text-amber-900 text-sm">
        This accounts ledger is restricted to HR Admin users. HR Viewer access remains aggregate-only.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-emerald-700">
            <ReceiptText className="w-4 h-4" />
            <span className="text-[11px] font-black uppercase tracking-wider">Accounts Reconciliation</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-1">Organisation Booking Ledger</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Booking-level financial records without employee or clinical identity data.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-semibold text-slate-700"
          >
            {periodOptions.map((option) => (
              <option key={option.key} value={option.key}>{option.label}</option>
            ))}
          </select>
          <button
            onClick={fetchLedger}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {!error && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Bookings</span>
                <CalendarDays className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-black text-slate-800 mt-2">{data?.total_bookings ?? '—'}</p>
              <span className="text-[10px] text-slate-400">Organisation activity in period</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Billable</span>
                <CircleDollarSign className="w-4 h-4 text-emerald-600" />
              </div>
              <p className="text-2xl font-black text-slate-800 mt-2">{data?.billable_bookings ?? '—'}</p>
              <span className="text-[10px] text-slate-400">Completed / billable sessions</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Invoiced</span>
                <FileCheck2 className="w-4 h-4 text-violet-600" />
              </div>
              <p className="text-2xl font-black text-slate-800 mt-2">{data?.invoiced_bookings ?? '—'}</p>
              <span className="text-[10px] text-slate-400">Linked to active invoices</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Billable Value</span>
                <ReceiptText className="w-4 h-4 text-amber-600" />
              </div>
              <p className="text-2xl font-black text-slate-800 mt-2">
                {data ? `${data.currency} ${Number(data.estimated_total || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
              </p>
              <span className="text-[10px] text-slate-400">Organisation rates, before invoice adjustments</span>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-slate-900 text-sm sm:text-base">Booking Reconciliation</h2>
                <p className="text-[11px] text-slate-400 mt-0.5">One safe accounting row per organisation booking.</p>
              </div>
            </div>

            {loading ? (
              <div className="py-12 text-center text-sm text-slate-500">Loading booking ledger…</div>
            ) : !data?.bookings?.length ? (
              <div className="py-12 text-center text-sm text-slate-500">No organisation bookings in this period.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide text-[10px]">
                    <tr>
                      <th className="px-5 py-3 font-bold">Booking Ref</th>
                      <th className="px-5 py-3 font-bold">Date</th>
                      <th className="px-5 py-3 font-bold">Service</th>
                      <th className="px-5 py-3 font-bold">Mode</th>
                      <th className="px-5 py-3 font-bold">Booking Status</th>
                      <th className="px-5 py-3 font-bold">Accounts</th>
                      <th className="px-5 py-3 font-bold text-right">Rate</th>
                      <th className="px-5 py-3 font-bold">Invoice</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.bookings.map((row) => (
                      <tr key={row.booking_reference} className="hover:bg-slate-50/70">
                        <td className="px-5 py-3 font-mono font-bold text-slate-700">{row.booking_reference}</td>
                        <td className="px-5 py-3 text-slate-600">{row.booking_date || '—'}</td>
                        <td className="px-5 py-3">
                          <div className="font-semibold text-slate-800">{row.service_name || labelize(row.session_type)}</div>
                          <div className="text-[10px] text-slate-400">{labelize(row.session_type)} counselling</div>
                        </td>
                        <td className="px-5 py-3 text-slate-600">{labelize(row.session_mode)}</td>
                        <td className="px-5 py-3">
                          <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-700 font-semibold">
                            {labelize(row.status)}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`px-2 py-1 rounded-full font-bold ${
                            row.billable
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-100 text-slate-500'
                          }`}>
                            {row.billable ? 'Billable' : 'Non-billable'}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right font-bold text-slate-800">
                          {row.billable ? `${row.currency} ${Number(row.unit_rate || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
                        </td>
                        <td className="px-5 py-3">
                          {row.invoice_number ? (
                            <div>
                              <div className="font-bold text-slate-800">{row.invoice_number}</div>
                              <div className="text-[10px] text-slate-400">{labelize(row.invoice_status)}</div>
                            </div>
                          ) : (
                            <span className="text-slate-400">Not invoiced</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-2xl flex items-start gap-3 text-xs text-emerald-900">
            <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <strong className="block font-bold">Accounts-only confidentiality boundary</strong>
              <p className="mt-0.5 leading-relaxed">
                {data?.privacy_notice || 'Employee identities and clinical information are not exposed in this ledger.'}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default HRBookingLedger;
