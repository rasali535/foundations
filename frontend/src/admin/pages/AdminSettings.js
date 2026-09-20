import React, { useState, useEffect } from 'react';
import { api } from '../AdminAuthContext';
import {
  Settings,
  Mail,
  MessageSquare,
  Shield,
  Clock,
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Info,
  Save,
  Receipt
} from 'lucide-react';
import { formatSessionDateTime } from '../AdminConstants';

const AdminSettings = () => {
  const [config, setConfig] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditLimit] = useState(25);
  const [actionFilter, setActionFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [invoiceProfile, setInvoiceProfile] = useState(null);
  const [invoiceProfileSaving, setInvoiceProfileSaving] = useState(false);
  const [invoiceProfileMessage, setInvoiceProfileMessage] = useState('');

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, notifRes, auditRes, invoiceProfileRes] = await Promise.all([
        api.get('/admin-ops/notifications/config'),
        api.get('/admin-ops/notifications?limit=50'),
        api.get('/admin-ops/audit/logs', { params: { page: auditPage, limit: auditLimit, action: actionFilter || undefined } }),
        api.get('/admin-ops/invoice-profile')
      ]);
      setConfig(cfgRes.data);
      setNotifications(notifRes.data || []);
      setAuditLogs(auditRes.data.logs || []);
      setAuditTotal(auditRes.data.total || 0);
      setInvoiceProfile(invoiceProfileRes.data);
    } catch (err) {
      console.error('Error fetching admin settings/logs:', err);
    } finally {
      setLoading(false);
    }
  }, [auditPage, auditLimit, actionFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateInvoiceProfileField = (field, value) => {
    setInvoiceProfile(prev => ({ ...(prev || {}), [field]: value }));
    setInvoiceProfileMessage('');
  };

  const saveInvoiceProfile = async () => {
    if (!invoiceProfile) return;
    setInvoiceProfileSaving(true);
    setInvoiceProfileMessage('');
    try {
      const res = await api.put('/admin-ops/invoice-profile', invoiceProfile);
      setInvoiceProfile(res.data);
      setInvoiceProfileMessage('Invoice company profile saved.');
    } catch (err) {
      setInvoiceProfileMessage(err.response?.data?.detail || 'Could not save invoice company profile.');
    } finally {
      setInvoiceProfileSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">System Settings & Telemetry</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Notification engines (Email & WhatsApp Cloud API), delivery logs, and immutable audit trails
          </p>
        </div>
      </div>

      {/* Invoice Company Profile */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Receipt className="w-5 h-5 text-emerald-700" />
              Invoice Company Profile
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Company identity and payment instructions printed on newly generated corporate invoices.
            </p>
          </div>
          <button
            type="button"
            onClick={saveInvoiceProfile}
            disabled={!invoiceProfile || invoiceProfileSaving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg"
          >
            <Save className="w-4 h-4" />
            {invoiceProfileSaving ? 'Saving...' : 'Save Invoice Profile'}
          </button>
        </div>

        {invoiceProfile && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <input value={invoiceProfile.legal_name || ''} onChange={(e) => updateInvoiceProfileField('legal_name', e.target.value)} placeholder="Legal company name" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.trading_name || ''} onChange={(e) => updateInvoiceProfileField('trading_name', e.target.value)} placeholder="Trading name" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.registration_number || ''} onChange={(e) => updateInvoiceProfileField('registration_number', e.target.value)} placeholder="Registration number" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.tax_number || ''} onChange={(e) => updateInvoiceProfileField('tax_number', e.target.value)} placeholder="Tax / VAT number" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.email || ''} onChange={(e) => updateInvoiceProfileField('email', e.target.value)} placeholder="Invoice email" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.phone || ''} onChange={(e) => updateInvoiceProfileField('phone', e.target.value)} placeholder="Phone" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <input value={invoiceProfile.website || ''} onChange={(e) => updateInvoiceProfileField('website', e.target.value)} placeholder="Website" className="px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <textarea value={invoiceProfile.address || ''} onChange={(e) => updateInvoiceProfileField('address', e.target.value)} placeholder="Business address" rows="2" className="sm:col-span-2 px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <textarea value={invoiceProfile.payment_instructions || ''} onChange={(e) => updateInvoiceProfileField('payment_instructions', e.target.value)} placeholder="Payment instructions shown on invoice" rows="2" className="sm:col-span-2 lg:col-span-3 px-3 py-2 border border-slate-200 rounded-lg text-xs" />
            <textarea value={invoiceProfile.footer_note || ''} onChange={(e) => updateInvoiceProfileField('footer_note', e.target.value)} placeholder="Invoice footer note" rows="2" className="sm:col-span-2 lg:col-span-3 px-3 py-2 border border-slate-200 rounded-lg text-xs" />
          </div>
        )}

        {invoiceProfileMessage && (
          <div className="text-xs font-semibold text-slate-600">{invoiceProfileMessage}</div>
        )}
      </div>

      {/* Provider Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Email Engine */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">Email Dispatch Engine</h3>
            </div>
            {config?.email_configured ? (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                Live SMTP
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                Dev Fallback Logger
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Sends HTML booking confirmations, batch multi-booking summaries, and reschedule advisories.
          </p>
          <div className="p-2.5 bg-slate-50 rounded-lg text-xs font-mono text-slate-600">
            Sender: {config?.email_sender || 'noreply@academyfoundations.com'}
          </div>
        </div>

        {/* WhatsApp Business API */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900 text-sm">WhatsApp Cloud API</h3>
            </div>
            {config?.whatsapp_configured ? (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                Live Meta API
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                Dev Fallback Logger
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Direct integration using Meta WhatsApp Cloud API for automated booking notifications.
          </p>
          <div className="p-2.5 bg-slate-50 rounded-lg text-xs font-mono text-slate-600 truncate">
            Phone ID: {config?.whatsapp_phone_number_id}
          </div>
        </div>

        {/* Operating Timezone */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-purple-600" />
              <h3 className="font-bold text-slate-900 text-sm">Clinical Timezone</h3>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800">
              CAT (UTC+2)
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Database timestamps are standardized in ISO UTC and converted consistently to Central Africa Time.
          </p>
          <div className="p-2.5 bg-slate-50 rounded-lg text-xs font-mono text-slate-600">
            Standard: Central Africa Time / Gaborone
          </div>
        </div>
      </div>

      {/* Notification Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
        <h3 className="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-2">
          <Mail className="w-4 h-4 text-emerald-600" />
          <span>Notification Transmission Log</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
              <tr>
                <th className="py-2.5 px-3">Channel</th>
                <th className="py-2.5 px-3">Recipient</th>
                <th className="py-2.5 px-3">Template / Subject</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Sent Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {notifications.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-6 text-center text-slate-400">No notification logs recorded.</td>
                </tr>
              ) : (
                notifications.map((n) => (
                  <tr key={n.id}>
                    <td className="py-2.5 px-3 font-semibold uppercase">{n.channel}</td>
                    <td className="py-2.5 px-3 font-mono">{n.recipient}</td>
                    <td className="py-2.5 px-3">{n.subject || n.template}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        n.status === 'sent' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {n.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">{formatSessionDateTime(n.sent_at || n.created_at).full}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Immutable Audit Log Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-2">
            <Shield className="w-4 h-4 text-purple-600" />
            <span>Immutable Platform Audit Trail</span>
          </h3>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="">All Actions</option>
            <option value="client_created">Client Created</option>
            <option value="intake_received">Intake Received</option>
            <option value="booking_created">Booking Created</option>
            <option value="booking_rescheduled">Booking Rescheduled</option>
            <option value="booking_cancelled">Booking Cancelled</option>
            <option value="email_sent">Email Sent</option>
            <option value="whatsapp_sent">WhatsApp Sent</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
              <tr>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Actor</th>
                <th className="py-2.5 px-3">Metadata Context</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan="4" className="py-6 text-center text-slate-400">No audit events recorded.</td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td className="py-2.5 px-3 font-mono text-slate-500">{formatSessionDateTime(log.created_at).full}</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900 capitalize">{log.action.replace(/_/g, ' ')}</td>
                    <td className="py-2.5 px-3 text-slate-600">{log.actor_name || log.actor_user_id || 'System / Client'}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {JSON.stringify(log.metadata || {})}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminSettings;
