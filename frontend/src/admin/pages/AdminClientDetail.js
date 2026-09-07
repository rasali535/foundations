import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  User,
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Building,
  FileText,
  Clock,
  Pin,
  Plus,
  Trash2,
  Edit2,
  CalendarPlus,
  Activity,
  AlertCircle,
  Video,
  Building2,
  X,
  Check,
  ShieldCheck,
  RotateCcw
} from 'lucide-react';
import { SESSION_TYPE_COLORS, SESSION_MODE_CONFIG, STATUS_CONFIG, formatSessionDateTime } from '../AdminConstants';

const AdminClientDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('bookings'); // bookings, intakes, notes, activity

  // Note creation state
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNotePinned, setNewNotePinned] = useState(false);
  const [noteSubmitting, setNoteSubmitting] = useState(false);

  // Quick Book modal state
  const [bookModalOpen, setBookModalOpen] = useState(false);
  const [therapists, setTherapists] = useState([]);
  const [bookForm, setBookForm] = useState({
    therapist_id: '',
    session_type: 'individual',
    session_mode: 'in_person',
    starts_at: '',
    notes: ''
  });
  const [bookLoading, setBookLoading] = useState(false);
  const [bookError, setBookError] = useState('');

  const fetchProfile = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/crm/clients/${id}`);
      setProfile(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load client profile.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchTherapists = React.useCallback(async () => {
    try {
      const res = await api.get('/therapists?active_only=true');
      setTherapists(res.data || []);
      if (res.data?.length > 0) {
        setBookForm(prev => ({ ...prev, therapist_id: res.data[0].id }));
      }
    } catch (err) {
      console.warn('Could not load therapists for booking modal:', err);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
    fetchTherapists();
  }, [fetchProfile, fetchTherapists]);

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!newNoteContent.trim()) return;
    setNoteSubmitting(true);
    try {
      await api.post(`/crm/clients/${id}/notes`, {
        content: newNoteContent.trim(),
        is_pinned: newNotePinned
      });
      setNewNoteContent('');
      setNewNotePinned(false);
      fetchProfile();
    } catch (err) {
      alert('Failed to save note.');
    } finally {
      setNoteSubmitting(false);
    }
  };

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm('Delete this administrative note?')) return;
    try {
      await api.delete(`/crm/notes/${noteId}`);
      fetchProfile();
    } catch (err) {
      alert('Failed to delete note.');
    }
  };

  const handleTogglePin = async (note) => {
    try {
      await api.put(`/crm/notes/${note.id}`, {
        is_pinned: !note.is_pinned
      });
      fetchProfile();
    } catch (err) {
      alert('Failed to toggle note pin.');
    }
  };

  const handleCreateBooking = async (e) => {
    e.preventDefault();
    setBookError('');
    setBookLoading(true);
    try {
      await api.post('/bookings', {
        client_id: id,
        therapist_id: bookForm.therapist_id,
        session_type: bookForm.session_type,
        session_mode: bookForm.session_mode,
        starts_at: new Date(bookForm.starts_at).toISOString(),
        notes: bookForm.notes,
        send_notifications: true,
        source: 'admin'
      });
      setBookModalOpen(false);
      setBookForm({
        therapist_id: therapists[0]?.id || '',
        session_type: 'individual',
        session_mode: 'in_person',
        starts_at: '',
        notes: ''
      });
      fetchProfile();
    } catch (err) {
      setBookError(err.response?.data?.detail || 'Failed to schedule booking.');
    } finally {
      setBookLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm text-slate-500">Loading client profile...</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto">
        <Link to="/admin/crm/clients" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Clients Directory</span>
        </Link>
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
          {error || 'Client profile not found.'}
        </div>
      </div>
    );
  }

  const { client, intakes, bookings, notes, activity_logs } = profile;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/admin/crm/clients"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Directory</span>
        </Link>
        <button
          onClick={() => setBookModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow transition"
        >
          <CalendarPlus className="w-4 h-4" />
          <span>Book Appointment</span>
        </button>
      </div>

      {/* Client Overview Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center font-black text-2xl shadow-md shrink-0">
              {client.first_name?.charAt(0)}{client.last_name?.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-black text-slate-900">
                  {client.first_name} {client.last_name}
                </h1>
                <span className="font-mono text-xs px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 font-bold border border-slate-200">
                  {client.client_number}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  client.status === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                }`}>
                  {client.status}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {client.organisation_name ? `Corporate Client (${client.organisation_name})` : 'Individual Private Client'}
              </p>

              {/* Contact metadata row */}
              <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span>{client.email || 'No email provided'}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{client.phone || 'No phone provided'}</span>
                </div>
                {client.location && (
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>{client.location}</span>
                  </div>
                )}
                {client.date_of_birth && (
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>DOB: {client.date_of_birth}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-100 rounded-xl shrink-0">
            <div className="text-center px-2">
              <span className="text-[11px] text-slate-400 font-medium">Sessions</span>
              <p className="text-lg font-black text-slate-800">{bookings.length}</p>
            </div>
            <div className="w-px h-8 bg-slate-200" />
            <div className="text-center px-2">
              <span className="text-[11px] text-slate-400 font-medium">Intakes</span>
              <p className="text-lg font-black text-slate-800">{intakes.length}</p>
            </div>
            <div className="w-px h-8 bg-slate-200" />
            <div className="text-center px-2">
              <span className="text-[11px] text-slate-400 font-medium">Admin Notes</span>
              <p className="text-lg font-black text-slate-800">{notes.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Profile Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-px">
        {[
          { key: 'bookings', label: `Bookings (${bookings.length})`, icon: Calendar },
          { key: 'intakes', label: `Intake History (${intakes.length})`, icon: FileText },
          { key: 'notes', label: `CRM Admin Notes (${notes.length})`, icon: Pin },
          { key: 'activity', label: `Activity Trail (${activity_logs.length})`, icon: Activity }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-t-xl transition-all border-b-2 ${
                isActive
                  ? 'border-emerald-600 text-emerald-700 bg-white shadow-sm'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Bookings */}
      {activeTab === 'bookings' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm">Client Appointment History</h3>
            <button
              onClick={() => setBookModalOpen(true)}
              className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-bold rounded-lg transition"
            >
              + Add Session
            </button>
          </div>
          <div className="divide-y divide-slate-100">
            {bookings.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No appointments booked for this client yet.
              </div>
            ) : (
              bookings.map((b) => {
                const typeConf = SESSION_TYPE_COLORS[b.session_type] || SESSION_TYPE_COLORS.individual;
                const modeConf = SESSION_MODE_CONFIG[b.session_mode] || SESSION_MODE_CONFIG.in_person;
                const statusConf = STATUS_CONFIG[b.status] || STATUS_CONFIG.confirmed;
                const dt = formatSessionDateTime(b.starts_at);

                return (
                  <div key={b.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60">
                    <div className="flex items-start gap-3">
                      <div className="flex flex-col items-center justify-center w-12 h-12 bg-slate-100 rounded-xl text-slate-700 shrink-0">
                        <span className="text-xs font-bold">{dt.time}</span>
                        <span className="text-[9px] text-slate-400">UTC</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">{dt.date}</span>
                          <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full ${typeConf.badge}`}>
                            {typeConf.label}
                          </span>
                          <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full ${modeConf.badge} flex items-center gap-1`}>
                            {b.session_mode === 'virtual' ? <Video className="w-2.5 h-2.5" /> : <Building2 className="w-2.5 h-2.5" />}
                            <span>{modeConf.label}</span>
                          </span>
                          <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full ${statusConf.badge}`}>
                            {statusConf.label}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Therapist: <strong className="text-slate-700">{b.therapist_name}</strong>
                          {b.location && ` • Location: ${b.location}`}
                        </p>
                        {b.virtual_meeting_link && (
                          <a href={b.virtual_meeting_link} target="_blank" rel="noreferrer" className="text-[11px] text-cyan-600 hover:underline mt-0.5 block">
                            Meeting Link: {b.virtual_meeting_link}
                          </a>
                        )}
                        {b.notes && <p className="text-[11px] text-slate-400 mt-0.5 italic">Note: {b.notes}</p>}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Intake Forms */}
      {activeTab === 'intakes' && (
        <div className="space-y-4">
          {intakes.length === 0 ? (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
              No intake forms recorded for this client.
            </div>
          ) : (
            intakes.map((intake, idx) => {
              const sub = intake.submission_data || {};
              const dt = formatSessionDateTime(intake.submitted_at || intake.created_at);
              return (
                <div key={intake.id} className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <FileText className="w-5 h-5 text-emerald-600" />
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm">
                          Intake Submission #{idx + 1}
                        </h4>
                        <span className="text-[11px] text-slate-400">Received on {dt.full}</span>
                      </div>
                    </div>
                    {intake.is_high_risk ? (
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                        High Priority Escalation
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-300">
                        Routine Counselling Triage
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="p-3 bg-slate-50 rounded-xl space-y-1.5">
                      <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Reason for Seeking Therapy</p>
                      <p className="text-slate-800 font-medium">{sub.reason_for_seeking_therapy || sub.reason || 'None specified'}</p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl space-y-1.5">
                      <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Emergency Contact</p>
                      <p className="text-slate-800">
                        {sub.emergency_contact_name || sub.emergency_name || 'N/A'} ({sub.emergency_contact_relationship || sub.emergency_relationship || 'Relation'}) • {sub.emergency_contact_phone || sub.emergency_phone || 'N/A'}
                      </p>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl space-y-1 text-xs">
                    <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Safety & Wellbeing Screen</p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                      <div>Self Harm: <strong>{sub.safety_screen?.self_harm || sub.self_harm || 'No'}</strong></div>
                      <div>Harm Others: <strong>{sub.safety_screen?.harm_others || sub.harm_others || 'No'}</strong></div>
                      <div>Unsafe Env: <strong>{sub.safety_screen?.unsafe_environment || sub.unsafe || 'No'}</strong></div>
                      <div>Abuse: <strong>{sub.safety_screen?.abuse_experienced || sub.abuse || 'No'}</strong></div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 3: CRM Administrative Notes */}
      {activeTab === 'notes' && (
        <div className="space-y-6">
          {/* Note Input Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5">
            <div className="mb-3">
              <h3 className="font-bold text-slate-900 text-sm">Add Administrative Note</h3>
              <p className="text-[11px] text-amber-700 font-medium bg-amber-50 px-2 py-1 rounded border border-amber-200 mt-1">
                Notice: Administrative CRM notes are for logistics, scheduling, and admin follow-ups only. Never enter confidential clinical assessments here.
              </p>
            </div>
            <form onSubmit={handleAddNote} className="space-y-3">
              <textarea
                required
                rows={3}
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="e.g. Client requested Tuesday morning slots. Resent confirmation SMS."
                className="w-full p-3 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-emerald-500"
              />
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newNotePinned}
                    onChange={(e) => setNewNotePinned(e.target.checked)}
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>Pin this note to top</span>
                </label>
                <button
                  type="submit"
                  disabled={noteSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {noteSubmitting ? 'Saving...' : 'Post Admin Note'}
                </button>
              </div>
            </form>
          </div>

          {/* Notes List */}
          <div className="space-y-3">
            {notes.length === 0 ? (
              <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
                No administrative notes added yet.
              </div>
            ) : (
              notes.map((note) => {
                const dt = formatSessionDateTime(note.created_at);
                return (
                  <div
                    key={note.id}
                    className={`bg-white rounded-xl border p-4 shadow-sm transition ${
                      note.is_pinned ? 'border-amber-300 bg-amber-50/20' : 'border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
                      <div className="flex items-center gap-2">
                        {note.is_pinned && (
                          <span className="flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
                            <Pin className="w-2.5 h-2.5" /> Pinned
                          </span>
                        )}
                        <span className="font-bold text-xs text-slate-800">{note.author_name}</span>
                        <span className="text-[10px] text-slate-400">• {dt.full}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTogglePin(note)}
                          className={`p-1 rounded text-xs ${note.is_pinned ? 'text-amber-600 hover:bg-amber-100' : 'text-slate-400 hover:bg-slate-100'}`}
                          title="Toggle Pin"
                        >
                          <Pin className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          className="p-1 rounded text-rose-400 hover:text-rose-600 hover:bg-rose-50"
                          title="Delete Note"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
                      {note.content}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Activity & Audit Trail */}
      {activeTab === 'activity' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5">
          <h3 className="font-bold text-slate-900 text-sm mb-4">Immutable Audit Trail for this Client</h3>
          <div className="space-y-3">
            {activity_logs.length === 0 ? (
              <p className="text-xs text-slate-400">No activity events recorded.</p>
            ) : (
              activity_logs.map((log) => {
                const dt = formatSessionDateTime(log.created_at);
                return (
                  <div key={log.id} className="text-xs border-l-2 border-emerald-500 pl-3 py-1 bg-slate-50/50 rounded-r-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 capitalize">
                        {log.action.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[10px] text-slate-400">{dt.full}</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Actor: {log.actor_name || log.actor_user_id || 'System / Client'}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Quick Booking Modal */}
      {bookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">Schedule Appointment for {client.first_name}</h3>
              <button onClick={() => setBookModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {bookError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{bookError}</span>
              </div>
            )}
            <form onSubmit={handleCreateBooking} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Session Type</label>
                  <select
                    value={bookForm.session_type}
                    onChange={(e) => setBookForm({ ...bookForm, session_type: e.target.value })}
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
                    value={bookForm.session_mode}
                    onChange={(e) => setBookForm({ ...bookForm, session_mode: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="in_person">In-Person (Clinic)</option>
                    <option value="virtual">Virtual (Video)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Therapist</label>
                <select
                  value={bookForm.therapist_id}
                  onChange={(e) => setBookForm({ ...bookForm, therapist_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                >
                  {therapists.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} {t.supports_in_person ? '(In-Person' : ''}{t.supports_virtual ? ' & Virtual)' : ')'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Start Date & Time (UTC)</label>
                <input
                  type="datetime-local"
                  required
                  value={bookForm.starts_at}
                  onChange={(e) => setBookForm({ ...bookForm, starts_at: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Session Notes (Optional)</label>
                <input
                  type="text"
                  value={bookForm.notes}
                  onChange={(e) => setBookForm({ ...bookForm, notes: e.target.value })}
                  placeholder="e.g. Initial intake review consultation"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setBookModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={bookLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {bookLoading ? 'Scheduling...' : 'Confirm Appointment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminClientDetail;
