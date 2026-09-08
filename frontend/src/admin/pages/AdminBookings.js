import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  CalendarDays,
  Plus,
  CalendarRange,
  RotateCcw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Video,
  Building2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Search,
  X,
  AlertCircle,
  Trash2
} from 'lucide-react';
import { SESSION_TYPE_COLORS, SESSION_MODE_CONFIG, STATUS_CONFIG, formatSessionDateTime } from '../AdminConstants';

const AdminBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(25);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [therapists, setTherapists] = useState([]);
  const [therapistFilter, setTherapistFilter] = useState('');
  const [loading, setLoading] = useState(true);

  // Modals
  const [singleModalOpen, setSingleModalOpen] = useState(false);
  const [multiModalOpen, setMultiModalOpen] = useState(false);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);

  // Single booking form state
  const [singleForm, setSingleForm] = useState({
    client_id: '',
    client_first_name: '',
    client_last_name: '',
    client_email: '',
    client_phone: '',
    therapist_id: '',
    session_type: 'individual',
    session_mode: 'in_person',
    starts_at: '',
    notes: '',
    participants: []
  });

  // Multi booking form state (monthly batch)
  const [multiForm, setMultiForm] = useState({
    client_id: '',
    client_first_name: '',
    client_last_name: '',
    client_email: '',
    client_phone: '',
    therapist_id: '',
    session_type: 'individual',
    session_mode: 'in_person',
    notes: '',
    slots: [
      { starts_at: '' },
      { starts_at: '' },
      { starts_at: '' },
      { starts_at: '' }
    ]
  });

  // Reschedule form state
  const [rescheduleForm, setRescheduleForm] = useState({
    new_starts_at: '',
    therapist_id: '',
    reason: ''
  });

  // Status form state
  const [statusForm, setStatusForm] = useState({
    status: 'completed',
    cancellation_reason: ''
  });

  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  const fetchBookings = React.useCallback(async (pageNum = 1) => {
    setLoading(true);
    try {
      const params = { page: pageNum, limit };
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.session_type = typeFilter;
      if (modeFilter) params.session_mode = modeFilter;
      if (therapistFilter) params.therapist_id = therapistFilter;

      const res = await api.get('/bookings', { params });
      setBookings(res.data.bookings || []);
      setTotal(res.data.total || 0);
      setPage(res.data.page || 1);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      console.error('Error fetching bookings:', err);
    } finally {
      setLoading(false);
    }
  }, [limit, statusFilter, typeFilter, modeFilter, therapistFilter]);

  const fetchTherapists = React.useCallback(async () => {
    try {
      const res = await api.get('/therapists');
      setTherapists(res.data || []);
      if (res.data?.length > 0) {
        setSingleForm(prev => ({ ...prev, therapist_id: res.data[0].id }));
        setMultiForm(prev => ({ ...prev, therapist_id: res.data[0].id }));
      }
    } catch (err) {
      console.warn('Could not load therapists:', err);
    }
  }, []);

  useEffect(() => {
    fetchTherapists();
  }, [fetchTherapists]);

  useEffect(() => {
    fetchBookings(1);
  }, [fetchBookings]);

  // Single Booking Submit
  const handleSingleSubmit = async (e) => {
    e.preventDefault();
    setActionError('');
    setActionLoading(true);
    try {
      await api.post('/bookings', {
        ...singleForm,
        starts_at: new Date(singleForm.starts_at).toISOString(),
        send_notifications: true
      });
      setSingleModalOpen(false);
      fetchBookings(1);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to create booking.');
    } finally {
      setActionLoading(false);
    }
  };

  // Multi Booking Submit (Monthly Multi-Booking)
  const handleMultiSubmit = async (e) => {
    e.preventDefault();
    setActionError('');
    setActionLoading(true);

    const validSlots = multiForm.slots
      .filter(s => s.starts_at)
      .map(s => ({ starts_at: new Date(s.starts_at).toISOString() }));

    if (validSlots.length === 0) {
      setActionError('Please specify at least one slot date/time.');
      setActionLoading(false);
      return;
    }

    try {
      await api.post('/bookings/multi', {
        ...multiForm,
        slots: validSlots,
        send_notifications: true
      });
      setMultiModalOpen(false);
      fetchBookings(1);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to create batch multi-booking.');
    } finally {
      setActionLoading(false);
    }
  };

  // Reschedule Submit
  const handleRescheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedBooking) return;
    setActionError('');
    setActionLoading(true);
    try {
      await api.post(`/bookings/${selectedBooking.id}/reschedule`, {
        new_starts_at: new Date(rescheduleForm.new_starts_at).toISOString(),
        therapist_id: rescheduleForm.therapist_id || selectedBooking.therapist_id,
        reason: rescheduleForm.reason,
        send_notifications: true
      });
      setRescheduleModalOpen(false);
      fetchBookings(page);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to reschedule.');
    } finally {
      setActionLoading(false);
    }
  };

  // Status Update Submit
  const handleStatusSubmit = async (e) => {
    e.preventDefault();
    if (!selectedBooking) return;
    setActionError('');
    setActionLoading(true);
    try {
      await api.post(`/bookings/${selectedBooking.id}/status`, {
        status: statusForm.status,
        cancellation_reason: statusForm.cancellation_reason,
        send_notifications: true
      });
      setStatusModalOpen(false);
      fetchBookings(page);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to update status.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">Booking Management</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Schedule single sessions, monthly multi-bookings, prevent double-bookings, and track session status
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              setActionError('');
              setMultiModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-xl transition"
          >
            <CalendarRange className="w-4 h-4" />
            <span>Monthly Multi-Book</span>
          </button>
          <button
            onClick={() => {
              setActionError('');
              setSingleModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Appointment</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap gap-3 items-center justify-between">
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="">All Statuses</option>
            <option value="confirmed">Confirmed</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
            <option value="late_cancelled_billable">Late Cancel (Billed)</option>
            <option value="no_show">No Show</option>
            <option value="pending">Pending</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="">All Types (Individual / Couple / Family)</option>
            <option value="individual">Individual (Blue)</option>
            <option value="couple">Couple (Purple)</option>
            <option value="family">Family (Green)</option>
          </select>

          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="">All Modes (In-Person / Virtual)</option>
            <option value="in_person">In-Person</option>
            <option value="virtual">Virtual</option>
          </select>

          <select
            value={therapistFilter}
            onChange={(e) => setTherapistFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="">All Therapists</option>
            {therapists.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Bookings Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Date & Time</th>
                <th className="py-3.5 px-4">Client</th>
                <th className="py-3.5 px-4">Type & Mode</th>
                <th className="py-3.5 px-4">Therapist</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <span>Loading appointments...</span>
                  </td>
                </tr>
              ) : bookings.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-500 font-medium">
                    No appointments found matching your filter criteria.
                  </td>
                </tr>
              ) : (
                bookings.map((booking) => {
                  const typeConf = SESSION_TYPE_COLORS[booking.session_type] || SESSION_TYPE_COLORS.individual;
                  const modeConf = SESSION_MODE_CONFIG[booking.session_mode] || SESSION_MODE_CONFIG.in_person;
                  const statusConf = STATUS_CONFIG[booking.status] || STATUS_CONFIG.confirmed;
                  const dt = formatSessionDateTime(booking.starts_at);

                  return (
                    <tr key={booking.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900 text-sm">{dt.date}</div>
                        <div className="text-slate-500 text-[11px] font-medium">{dt.time} UTC</div>
                        {booking.booking_batch_id && (
                          <span className="text-[9px] font-semibold text-indigo-600 bg-indigo-50 px-1 py-0.2 rounded mt-0.5 inline-block">
                            Monthly Batch
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <Link
                          to={`/admin/crm/clients/${booking.client_id}`}
                          className="font-bold text-slate-900 hover:text-emerald-600 transition block text-sm"
                        >
                          {booking.client_name}
                        </Link>
                        <span className="text-[10px] text-slate-400">{booking.client_number}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${typeConf.badge}`}>
                            {typeConf.label}
                          </span>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${modeConf.badge} flex items-center gap-1`}>
                            {booking.session_mode === 'virtual' ? <Video className="w-3 h-3" /> : <Building2 className="w-3 h-3" />}
                            <span>{modeConf.label}</span>
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">
                        {booking.therapist_name}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold ${statusConf.badge}`}>
                          {statusConf.label}
                        </span>
                        {booking.status === 'late_cancelled_billable' && booking.hours_before_session != null && (
                          <div className="mt-0.5 text-[9px] text-orange-600 font-semibold">
                            {booking.hours_before_session.toFixed(1)}h before session
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setSelectedBooking(booking);
                              setRescheduleForm({
                                new_starts_at: booking.starts_at.substring(0, 16),
                                therapist_id: booking.therapist_id,
                                reason: ''
                              });
                              setActionError('');
                              setRescheduleModalOpen(true);
                            }}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                          >
                            Reschedule
                          </button>
                          <button
                            onClick={() => {
                              setSelectedBooking(booking);
                              setStatusForm({
                                status: booking.status === 'confirmed' ? 'completed' : booking.status,
                                cancellation_reason: ''
                              });
                              setActionError('');
                              setStatusModalOpen(true);
                            }}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                          >
                            Status
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing <strong className="text-slate-800">{bookings.length}</strong> of <strong className="text-slate-800">{total}</strong> appointments
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => fetchBookings(page - 1)}
              className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-slate-700">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => fetchBookings(page + 1)}
              className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Single Booking Modal */}
      {singleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">Create Single Appointment</h3>
              <button onClick={() => setSingleModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleSingleSubmit} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client First Name *</label>
                  <input
                    type="text"
                    required
                    value={singleForm.client_first_name}
                    onChange={(e) => setSingleForm({ ...singleForm, client_first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Last Name</label>
                  <input
                    type="text"
                    value={singleForm.client_last_name}
                    onChange={(e) => setSingleForm({ ...singleForm, client_last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Email *</label>
                  <input
                    type="email"
                    required
                    value={singleForm.client_email}
                    onChange={(e) => setSingleForm({ ...singleForm, client_email: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Phone</label>
                  <input
                    type="text"
                    value={singleForm.client_phone}
                    onChange={(e) => setSingleForm({ ...singleForm, client_phone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Session Type</label>
                  <select
                    value={singleForm.session_type}
                    onChange={(e) => setSingleForm({ ...singleForm, session_type: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="individual">Individual (Blue)</option>
                    <option value="couple">Couple (Purple)</option>
                    <option value="family">Family (Green)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Session Mode</label>
                  <select
                    value={singleForm.session_mode}
                    onChange={(e) => setSingleForm({ ...singleForm, session_mode: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="in_person">In-Person</option>
                    <option value="virtual">Virtual</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Therapist</label>
                <select
                  value={singleForm.therapist_id}
                  onChange={(e) => setSingleForm({ ...singleForm, therapist_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  {therapists.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Start Date & Time (UTC) *</label>
                <input
                  type="datetime-local"
                  required
                  value={singleForm.starts_at}
                  onChange={(e) => setSingleForm({ ...singleForm, starts_at: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setSingleModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Verifying & Booking...' : 'Confirm Single Booking'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Monthly Multi-Booking Modal */}
      {multiModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <CalendarRange className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-900 text-base">Monthly Multi-Booking Batch</h3>
              </div>
              <button onClick={() => setMultiModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2 shrink-0">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleMultiSubmit} className="p-5 space-y-4 overflow-y-auto flex-1">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client First Name *</label>
                  <input
                    type="text"
                    required
                    value={multiForm.client_first_name}
                    onChange={(e) => setMultiForm({ ...multiForm, client_first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Last Name</label>
                  <input
                    type="text"
                    value={multiForm.client_last_name}
                    onChange={(e) => setMultiForm({ ...multiForm, client_last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Email *</label>
                  <input
                    type="email"
                    required
                    value={multiForm.client_email}
                    onChange={(e) => setMultiForm({ ...multiForm, client_email: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Client Phone</label>
                  <input
                    type="text"
                    value={multiForm.client_phone}
                    onChange={(e) => setMultiForm({ ...multiForm, client_phone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Session Type</label>
                  <select
                    value={multiForm.session_type}
                    onChange={(e) => setMultiForm({ ...multiForm, session_type: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="individual">Individual (Blue)</option>
                    <option value="couple">Couple (Purple)</option>
                    <option value="family">Family (Green)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Session Mode</label>
                  <select
                    value={multiForm.session_mode}
                    onChange={(e) => setMultiForm({ ...multiForm, session_mode: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="in_person">In-Person</option>
                    <option value="virtual">Virtual</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Therapist</label>
                <select
                  value={multiForm.therapist_id}
                  onChange={(e) => setMultiForm({ ...multiForm, therapist_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  {therapists.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              {/* Multi-Slots Section */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">Monthly Session Dates & Times (UTC)</span>
                  <span className="text-[10px] text-slate-400">Atomic Conflict Pre-Check</span>
                </div>
                {multiForm.slots.map((slot, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-500 w-16">Slot #{idx + 1}:</span>
                    <input
                      type="datetime-local"
                      value={slot.starts_at}
                      onChange={(e) => {
                        const newSlots = [...multiForm.slots];
                        newSlots[idx].starts_at = e.target.value;
                        setMultiForm({ ...multiForm, slots: newSlots });
                      }}
                      className="flex-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs"
                    />
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setMultiModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Pre-Checking & Booking...' : 'Confirm Multi-Booking Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reschedule Modal */}
      {rescheduleModalOpen && selectedBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">Reschedule Appointment</h3>
              <button onClick={() => setRescheduleModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleRescheduleSubmit} className="p-5 space-y-4">
              <p className="text-xs text-slate-500">
                Rescheduling session for <strong className="text-slate-800">{selectedBooking.client_name}</strong> (Currently: {selectedBooking.starts_at})
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">New Start Time (UTC) *</label>
                <input
                  type="datetime-local"
                  required
                  value={rescheduleForm.new_starts_at}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, new_starts_at: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Therapist</label>
                <select
                  value={rescheduleForm.therapist_id}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, therapist_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  {therapists.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reschedule Reason</label>
                <input
                  type="text"
                  value={rescheduleForm.reason}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, reason: e.target.value })}
                  placeholder="e.g. Client work travel"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setRescheduleModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Validating Slot...' : 'Confirm Reschedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Status Update Modal */}
      {statusModalOpen && selectedBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">Update Appointment Status</h3>
              <button onClick={() => setStatusModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleStatusSubmit} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">New Status</label>
                <select
                  value={statusForm.status}
                  onChange={(e) => setStatusForm({ ...statusForm, status: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled (≥ 6 hrs notice — not billed)</option>
                  <option value="no_show">No Show</option>
                  <option value="confirmed">Confirmed</option>
                </select>
                <p className="text-[10px] text-slate-500 mt-1">
                  Selecting <strong>Cancelled</strong> will apply the FCA 6-hour policy automatically.
                  If the cancellation timestamp is less than 6 hours before the session, the backend will classify it as <span className="text-orange-700 font-semibold">Late Cancellation (Billable)</span>.
                </p>
              </div>

              {statusForm.status === 'cancelled' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Cancellation Reason</label>
                  <input
                    type="text"
                    required
                    value={statusForm.cancellation_reason}
                    onChange={(e) => setStatusForm({ ...statusForm, cancellation_reason: e.target.value })}
                    placeholder="e.g. Client requested cancellation"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              )}

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setStatusModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Updating...' : 'Update Status'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminBookings;
