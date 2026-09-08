import React, { useState, useEffect } from 'react';
import { api } from '../AdminAuthContext';
import {
  UserCheck,
  Plus,
  CalendarOff,
  Video,
  Building2,
  Trash2,
  Edit2,
  CheckCircle,
  XCircle,
  X,
  AlertCircle,
  MessageCircle
} from 'lucide-react';
import { formatSessionDateTime } from '../AdminConstants';

const AdminTherapists = () => {
  const [therapists, setTherapists] = useState([]);
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [therapistModalOpen, setTherapistModalOpen] = useState(false);
  const [blockModalOpen, setBlockModalOpen] = useState(false);
  const [editingTherapist, setEditingTherapist] = useState(null);

  const [therapistForm, setTherapistForm] = useState({
    name: '',
    email: '',
    phone: '',
    whatsapp_phone: '',
    whatsapp_notifications_enabled: false,
    supports_in_person: true,
    supports_virtual: true,
    specializations: '',
    working_hours_start: '08:00',
    working_hours_end: '17:00',
    default_location: ''
  });

  const [blockForm, setBlockForm] = useState({
    therapist_id: '',
    type: 'leave',
    starts_at: '',
    ends_at: '',
    reason: ''
  });

  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  const fetchTherapistsAndBlocks = React.useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, bRes] = await Promise.all([
        api.get('/therapists'),
        api.get('/therapists/blocks')
      ]);
      setTherapists(tRes.data || []);
      setBlocks(bRes.data || []);
      if (tRes.data?.length > 0) {
        setBlockForm(prev => ({ ...prev, therapist_id: prev.therapist_id || tRes.data[0].id }));
      }
    } catch (err) {
      console.error('Error fetching therapists/blocks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTherapistsAndBlocks();
  }, [fetchTherapistsAndBlocks]);

  const handleSaveTherapist = async (e) => {
    e.preventDefault();
    setActionError('');
    setActionLoading(true);
    try {
      const {
        whatsapp_phone,
        whatsapp_notifications_enabled,
        ...baseTherapistForm
      } = therapistForm;

      const payload = {
        ...baseTherapistForm,
        specializations: typeof therapistForm.specializations === 'string'
          ? therapistForm.specializations.split(',').map(s => s.trim()).filter(Boolean)
          : therapistForm.specializations
      };

      // Required FCA seed therapists may intentionally have no verified email yet.
      // Do not overwrite a missing email with an invalid empty string during edits.
      if (editingTherapist && !payload.email) {
        delete payload.email;
      }

      let savedTherapist;
      if (editingTherapist) {
        const res = await api.put(`/therapists/${editingTherapist.id}`, payload);
        savedTherapist = res.data;
      } else {
        const res = await api.post('/therapists', payload);
        savedTherapist = res.data;
      }

      await api.patch(`/therapists/${savedTherapist.id}/notifications`, {
        whatsapp_phone: whatsapp_phone || null,
        whatsapp_notifications_enabled
      });

      setTherapistModalOpen(false);
      setEditingTherapist(null);
      fetchTherapistsAndBlocks();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to save therapist.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateBlock = async (e) => {
    e.preventDefault();
    setActionError('');
    setActionLoading(true);
    try {
      await api.post('/therapists/blocks', {
        ...blockForm,
        starts_at: new Date(blockForm.starts_at).toISOString(),
        ends_at: new Date(blockForm.ends_at).toISOString()
      });
      setBlockModalOpen(false);
      setBlockForm({
        therapist_id: therapists[0]?.id || '',
        type: 'leave',
        starts_at: '',
        ends_at: '',
        reason: ''
      });
      fetchTherapistsAndBlocks();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to schedule leave/block.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteBlock = async (blockId) => {
    if (!window.confirm('Delete this therapist block?')) return;
    try {
      await api.delete(`/therapists/blocks/${blockId}`);
      fetchTherapistsAndBlocks();
    } catch (err) {
      alert('Failed to delete block.');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">Therapists & Availability</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Configure clinical staff capabilities, in-person/virtual routing, working hours, leave schedules, and internal notifications
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              setActionError('');
              setBlockModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-bold rounded-xl transition"
          >
            <CalendarOff className="w-4 h-4" />
            <span>Schedule Leave / Block</span>
          </button>
          <button
            onClick={() => {
              setEditingTherapist(null);
              setTherapistForm({
                name: '',
                email: '',
                phone: '',
                whatsapp_phone: '',
                whatsapp_notifications_enabled: false,
                supports_in_person: true,
                supports_virtual: true,
                specializations: '',
                working_hours_start: '08:00',
                working_hours_end: '17:00',
                default_location: ''
              });
              setActionError('');
              setTherapistModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Therapist</span>
          </button>
        </div>
      </div>

      {/* Therapists Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-3 py-12 text-center text-slate-400">Loading therapists...</div>
        ) : (
          therapists.map((t) => (
            <div key={t.id} className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 text-base">{t.name}</h3>
                  <p className="text-xs text-slate-500">{t.email || 'Email not verified'}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  t.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                }`}>
                  {t.active ? 'Active' : 'Inactive'}
                </span>
              </div>

              {/* Capabilities */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Session Capabilities</span>
                <div className="flex flex-wrap gap-1.5">
                  {t.supports_in_person && (
                    <span className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                      <Building2 className="w-3 h-3" /> In-Person
                    </span>
                  )}
                  {t.supports_virtual && (
                    <span className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200">
                      <Video className="w-3 h-3" /> Virtual
                    </span>
                  )}
                </div>
              </div>

              {/* Notification Status */}
              <div className="p-3 bg-emerald-50/60 border border-emerald-100 rounded-xl space-y-1.5 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-1.5 font-semibold text-slate-700">
                    <MessageCircle className="w-3.5 h-3.5 text-emerald-600" /> Therapist WhatsApp
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    t.whatsapp_notifications_enabled
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {t.whatsapp_notifications_enabled ? 'Enabled' : 'Off'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500">
                  {t.whatsapp_phone || 'WhatsApp number not set'}
                </p>
              </div>

              {/* Working Hours */}
              <div className="p-3 bg-slate-50 rounded-xl space-y-1 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Hours:</span>
                  <strong className="text-slate-800">{t.working_hours_start} - {t.working_hours_end} UTC</strong>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Slot Length:</span>
                  <strong className="text-slate-800">{t.slot_duration_minutes} mins</strong>
                </div>
              </div>

              {/* Specializations */}
              {t.specializations?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Specializations</span>
                  <div className="flex flex-wrap gap-1">
                    {t.specializations.map((s, idx) => (
                      <span key={idx} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-slate-100 flex justify-end">
                <button
                  onClick={() => {
                    setEditingTherapist(t);
                    setTherapistForm({
                      name: t.name,
                      email: t.email || '',
                      phone: t.phone || '',
                      whatsapp_phone: t.whatsapp_phone || '',
                      whatsapp_notifications_enabled: Boolean(t.whatsapp_notifications_enabled),
                      supports_in_person: t.supports_in_person,
                      supports_virtual: t.supports_virtual,
                      specializations: Array.isArray(t.specializations) ? t.specializations.join(', ') : '',
                      working_hours_start: t.working_hours_start || '08:00',
                      working_hours_end: t.working_hours_end || '17:00',
                      default_location: t.default_location || ''
                    });
                    setActionError('');
                    setTherapistModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600 hover:text-emerald-700"
                >
                  <Edit2 className="w-3 h-3" />
                  <span>Configure</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Leave & Blocked Intervals Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
        <h3 className="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-2">
          <CalendarOff className="w-4 h-4 text-amber-600" />
          <span>Active Leave & Admin Block Intervals</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
              <tr>
                <th className="py-2.5 px-3">Therapist ID</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Start Time (UTC)</th>
                <th className="py-2.5 px-3">End Time (UTC)</th>
                <th className="py-2.5 px-3">Reason</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {blocks.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-6 text-center text-slate-400">
                    No active leave or blocked intervals.
                  </td>
                </tr>
              ) : (
                blocks.map((blk) => (
                  <tr key={blk.id}>
                    <td className="py-2.5 px-3 font-semibold text-slate-800">{blk.therapist_id}</td>
                    <td className="py-2.5 px-3 capitalize">{blk.type.replace(/_/g, ' ')}</td>
                    <td className="py-2.5 px-3">{formatSessionDateTime(blk.starts_at).full}</td>
                    <td className="py-2.5 px-3">{formatSessionDateTime(blk.ends_at).full}</td>
                    <td className="py-2.5 px-3 text-slate-500">{blk.reason || 'None specified'}</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleDeleteBlock(blk.id)}
                        className="p-1 text-rose-400 hover:text-rose-600 rounded"
                        title="Remove Block"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Therapist Modal */}
      {therapistModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden max-h-[92vh] overflow-y-auto">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">
                {editingTherapist ? `Edit Therapist: ${editingTherapist.name}` : 'Add New Therapist'}
              </h3>
              <button onClick={() => setTherapistModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleSaveTherapist} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={therapistForm.name}
                  onChange={(e) => setTherapistForm({ ...therapistForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Email Address {editingTherapist ? '' : '*'}
                  </label>
                  <input
                    type="email"
                    required={!editingTherapist}
                    value={therapistForm.email}
                    onChange={(e) => setTherapistForm({ ...therapistForm, email: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number</label>
                  <input
                    type="text"
                    value={therapistForm.phone}
                    onChange={(e) => setTherapistForm({ ...therapistForm, phone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              {/* Therapist WhatsApp Notifications */}
              <div className="p-3 bg-emerald-50/60 border border-emerald-100 rounded-xl space-y-3">
                <div className="flex items-center gap-2">
                  <MessageCircle className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-bold text-slate-800">Therapist Booking Notifications</span>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">WhatsApp Number</label>
                  <input
                    type="text"
                    value={therapistForm.whatsapp_phone}
                    onChange={(e) => setTherapistForm({ ...therapistForm, whatsapp_phone: e.target.value })}
                    placeholder="+267XXXXXXXX"
                    className="w-full px-3 py-2 border border-emerald-200 bg-white rounded-lg text-xs"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Use full international E.164 format. FCA will not guess a country code.</p>
                </div>
                <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={therapistForm.whatsapp_notifications_enabled}
                    onChange={(e) => setTherapistForm({ ...therapistForm, whatsapp_notifications_enabled: e.target.checked })}
                    className="mt-0.5 rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>
                    Send booking and reschedule confirmations to this therapist on WhatsApp.
                    Messages contain scheduling/logistics only, never intake or clinical content.
                  </span>
                </label>
              </div>

              {/* Capabilities Checkboxes */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-slate-800 block">Routing Capabilities</span>
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={therapistForm.supports_in_person}
                      onChange={(e) => setTherapistForm({ ...therapistForm, supports_in_person: e.target.checked })}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Supports In-Person Sessions</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={therapistForm.supports_virtual}
                      onChange={(e) => setTherapistForm({ ...therapistForm, supports_virtual: e.target.checked })}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Supports Virtual Sessions</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Working Hours Start</label>
                  <input
                    type="text"
                    value={therapistForm.working_hours_start}
                    onChange={(e) => setTherapistForm({ ...therapistForm, working_hours_start: e.target.value })}
                    placeholder="08:00"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Working Hours End</label>
                  <input
                    type="text"
                    value={therapistForm.working_hours_end}
                    onChange={(e) => setTherapistForm({ ...therapistForm, working_hours_end: e.target.value })}
                    placeholder="17:00"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Specializations (comma separated)</label>
                <input
                  type="text"
                  value={therapistForm.specializations}
                  onChange={(e) => setTherapistForm({ ...therapistForm, specializations: e.target.value })}
                  placeholder="e.g. Individual, Couples, Trauma, EAP"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setTherapistModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Save Therapist'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Schedule Leave / Block Modal */}
      {blockModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">Schedule Leave / Block Interval</h3>
              <button onClick={() => setBlockModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleCreateBlock} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Therapist</label>
                <select
                  value={blockForm.therapist_id}
                  onChange={(e) => setBlockForm({ ...blockForm, therapist_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  {therapists.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Block Type</label>
                <select
                  value={blockForm.type}
                  onChange={(e) => setBlockForm({ ...blockForm, type: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="leave">Annual / Personal Leave</option>
                  <option value="blocked_slot">Manual Slot Block</option>
                  <option value="public_holiday">Public Holiday</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Start Time (UTC) *</label>
                  <input
                    type="datetime-local"
                    required
                    value={blockForm.starts_at}
                    onChange={(e) => setBlockForm({ ...blockForm, starts_at: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">End Time (UTC) *</label>
                  <input
                    type="datetime-local"
                    required
                    value={blockForm.ends_at}
                    onChange={(e) => setBlockForm({ ...blockForm, ends_at: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reason / Notes</label>
                <input
                  type="text"
                  value={blockForm.reason}
                  onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                  placeholder="e.g. Clinical conference in Maun"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setBlockModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Saving Block...' : 'Save Block'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminTherapists;
