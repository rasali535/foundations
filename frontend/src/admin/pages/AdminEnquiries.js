import React, { useEffect, useMemo, useState } from 'react';
import { Mail, MessageSquareText, RefreshCw, CheckCircle2, AlertCircle, Search } from 'lucide-react';
import { api } from '../AdminAuthContext';

const formatTime = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const DeliveryBadge = ({ status }) => {
  if (status === 'sent') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="w-3 h-3" /> Resend accepted
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[10px] font-bold text-rose-700 border border-rose-200">
        <AlertCircle className="w-3 h-3" /> Email failed
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-500 border border-slate-200">
      Not sent yet
    </span>
  );
};

const AdminEnquiries = () => {
  const [contacts, setContacts] = useState([]);
  const [leads, setLeads] = useState([]);
  const [tab, setTab] = useState('contacts');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [contactRes, leadRes] = await Promise.all([
        api.get('/contact'),
        api.get('/chat/leads')
      ]);
      setContacts(contactRes.data || []);
      setLeads(leadRes.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load enquiries.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const rows = tab === 'contacts' ? contacts : leads;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((item) =>
      [
        item.name,
        item.email,
        item.company,
        item.phone,
        item.inquiry_type,
        item.message,
        item.notes
      ].some((value) => String(value || '').toLowerCase().includes(needle))
    );
  }, [rows, query]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Website CRM</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Enquiries & Leads</h1>
          <p className="text-sm text-slate-500 mt-1">Saved website submissions remain here even if email delivery is temporarily unavailable.</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="flex gap-2">
            <button
              onClick={() => setTab('contacts')}
              className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${tab === 'contacts' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'}`}
            >
              <Mail className="w-4 h-4" /> Contact forms ({contacts.length})
            </button>
            <button
              onClick={() => setTab('leads')}
              className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${tab === 'leads' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'}`}
            >
              <MessageSquareText className="w-4 h-4" /> Chat leads ({leads.length})
            </button>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search enquiries"
              className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
        </div>

        {error && <div className="m-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

        {loading ? (
          <div className="p-12 text-center text-sm text-slate-400">Loading enquiries…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-400">No matching enquiries.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((item) => (
              <article key={item.id || item.session_id} className="p-5 hover:bg-slate-50/50">
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-bold text-slate-900">{item.name || 'Unnamed visitor'}</h2>
                      <span className="text-xs text-slate-400">{formatTime(item.created_at)}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      {item.email && <span>{item.email}</span>}
                      {item.phone && <span>{item.phone}</span>}
                      {item.company && <span>{item.company}</span>}
                      {item.inquiry_type && <span className="font-semibold text-slate-700">{item.inquiry_type}</span>}
                    </div>
                    {(item.message || item.notes) && (
                      <p className="mt-3 max-w-4xl whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.message || item.notes}</p>
                    )}
                  </div>
                  <div className="shrink-0">
                    <DeliveryBadge status={item.admin_notification_status || item.notification_status} />
                    {tab === 'contacts' && (
                      <div className="mt-2 text-[10px] text-slate-400">
                        Sender acknowledgement: {item.acknowledgement_status || 'not recorded'}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminEnquiries;
