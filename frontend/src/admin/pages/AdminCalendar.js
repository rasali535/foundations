import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Video,
  Building2,
  Clock,
  User,
  X,
  Filter,
  Eye,
  CalendarDays
} from 'lucide-react';
import { SESSION_TYPE_COLORS, SESSION_MODE_CONFIG, STATUS_CONFIG, formatSessionDateTime } from '../AdminConstants';

const AdminCalendar = () => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('month'); // month, week, day
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [therapists, setTherapists] = useState([]);
  const [therapistFilter, setTherapistFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedBooking, setSelectedBooking] = useState(null);

  const fetchCalendarBookings = React.useCallback(async () => {
    setLoading(true);
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
      const firstDay = new Date(Date.UTC(year, month - 1, 20)).toISOString();
      const lastDay = new Date(Date.UTC(year, month + 2, 10)).toISOString();

      const params = {
        start_date: firstDay,
        end_date: lastDay,
        limit: 200
      };
      if (therapistFilter) params.therapist_id = therapistFilter;
      if (typeFilter) params.session_type = typeFilter;

      const res = await api.get('/bookings', { params });
      setBookings(res.data.bookings || []);
    } catch (err) {
      console.error('Error fetching calendar bookings:', err);
    } finally {
      setLoading(false);
    }
  }, [currentDate, therapistFilter, typeFilter]);

  const fetchTherapists = React.useCallback(async () => {
    try {
      const res = await api.get('/therapists');
      setTherapists(res.data || []);
    } catch (e) {
      console.warn('Could not load therapists:', e);
    }
  }, []);

  useEffect(() => {
    fetchTherapists();
  }, [fetchTherapists]);

  useEffect(() => {
    fetchCalendarBookings();
  }, [fetchCalendarBookings]);

  const prevPeriod = () => {
    const d = new Date(currentDate);
    if (viewMode === 'month') d.setMonth(d.getMonth() - 1);
    else if (viewMode === 'week') d.setDate(d.getDate() - 7);
    else d.setDate(d.getDate() - 1);
    setCurrentDate(d);
  };

  const nextPeriod = () => {
    const d = new Date(currentDate);
    if (viewMode === 'month') d.setMonth(d.getMonth() + 1);
    else if (viewMode === 'week') d.setDate(d.getDate() + 7);
    else d.setDate(d.getDate() + 1);
    setCurrentDate(d);
  };

  const setToday = () => {
    setCurrentDate(new Date());
  };

  // Helper to build month grid days
  const getDaysInMonth = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDayIndex = new Date(year, month, 1).getDay(); // 0=Sun
    const totalDays = new Date(year, month + 1, 0).getDate();

    const days = [];
    // Padding before month start
    for (let i = 0; i < firstDayIndex; i++) {
      days.push({ dayNumber: null, isCurrentMonth: false });
    }
    for (let d = 1; d <= totalDays; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({ dayNumber: d, dateStr, isCurrentMonth: true });
    }
    return days;
  };

  const monthName = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">Clinical Calendar</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Visual appointment schedule • Color-coded: Blue (Individual), Purple (Couple), Green (Family)
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <span className="w-2 h-2 rounded-full bg-blue-500" /> Individual
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <span className="w-2 h-2 rounded-full bg-purple-500" /> Couple
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Family
          </span>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={prevPeriod}
            className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={setToday}
            className="px-3 py-1.5 border border-slate-200 hover:bg-slate-50 rounded-lg text-xs font-bold text-slate-700"
          >
            Today
          </button>
          <button
            onClick={nextPeriod}
            className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <h2 className="text-base font-black text-slate-800 ml-2">{monthName}</h2>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={therapistFilter}
            onChange={(e) => setTherapistFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
          >
            <option value="">All Therapists</option>
            {therapists.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
          >
            <option value="">All Types</option>
            <option value="individual">Individual</option>
            <option value="couple">Couple</option>
            <option value="family">Family</option>
          </select>

          {/* View Mode Buttons */}
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
            {['month', 'week', 'day'].map((v) => (
              <button
                key={v}
                onClick={() => setViewMode(v)}
                className={`px-3 py-1 text-xs font-bold rounded-md capitalize transition ${
                  viewMode === v ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Month View Grid */}
      {viewMode === 'month' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
          {/* Days of Week Header */}
          <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50 text-center text-xs font-bold text-slate-600 py-3">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
              <div key={d}>{d}</div>
            ))}
          </div>

          {/* Day Cells Grid */}
          <div className="grid grid-cols-7 divide-x divide-y divide-slate-100 min-h-[600px]">
            {getDaysInMonth().map((item, idx) => {
              if (!item.isCurrentMonth) {
                return <div key={idx} className="bg-slate-50/50 p-2 min-h-[110px]" />;
              }

              const isToday =
                new Date().toISOString().substring(0, 10) === item.dateStr;

              // Find bookings for this day
              const dayBookings = bookings.filter(
                b => b.starts_at && b.starts_at.substring(0, 10) === item.dateStr
              );

              return (
                <div
                  key={idx}
                  className={`p-2 min-h-[110px] flex flex-col justify-between transition hover:bg-slate-50/70 ${
                    isToday ? 'bg-emerald-50/30' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={`text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full ${
                        isToday ? 'bg-emerald-600 text-white' : 'text-slate-700'
                      }`}
                    >
                      {item.dayNumber}
                    </span>
                    {dayBookings.length > 0 && (
                      <span className="text-[10px] text-slate-400 font-semibold">
                        {dayBookings.length} session{dayBookings.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>

                  {/* Bookings inside Day Cell */}
                  <div className="space-y-1 overflow-y-auto max-h-24">
                    {dayBookings.map((b) => {
                      const typeConf = SESSION_TYPE_COLORS[b.session_type] || SESSION_TYPE_COLORS.individual;
                      const timeStr = b.starts_at.substring(11, 16);

                      return (
                        <button
                          key={b.id}
                          onClick={() => setSelectedBooking(b)}
                          className={`w-full text-left p-1 rounded-md text-[10px] font-semibold border truncate block transition ${typeConf.badge} hover:brightness-95`}
                        >
                          <div className="flex items-center gap-1">
                            <span className="font-mono">{timeStr}</span>
                            <span className="truncate">{b.client_name}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Week / Day View Placeholder Feed */}
      {(viewMode === 'week' || viewMode === 'day') && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
          <h3 className="font-bold text-slate-900 text-base mb-4">
            Appointments List ({viewMode === 'week' ? 'Weekly Scope' : 'Day Scope'})
          </h3>
          <div className="divide-y divide-slate-100">
            {bookings.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No appointments in this period.</p>
            ) : (
              bookings.map((b) => {
                const typeConf = SESSION_TYPE_COLORS[b.session_type] || SESSION_TYPE_COLORS.individual;
                const modeConf = SESSION_MODE_CONFIG[b.session_mode] || SESSION_MODE_CONFIG.in_person;
                const dt = formatSessionDateTime(b.starts_at);
                return (
                  <div key={b.id} className="py-3 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900">{dt.full} UTC</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full ${typeConf.badge}`}>
                          {typeConf.label}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full ${modeConf.badge}`}>
                          {modeConf.label}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Client: <strong className="text-slate-800">{b.client_name}</strong> • Therapist: {b.therapist_name}
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedBooking(b)}
                      className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                    >
                      Inspect
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Booking Inspector Modal */}
      {selectedBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-base">Appointment Details</h3>
              <button onClick={() => setSelectedBooking(null)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl space-y-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase">Client</p>
                <Link
                  to={`/admin/crm/clients/${selectedBooking.client_id}`}
                  className="font-bold text-slate-900 hover:text-emerald-600 text-sm block"
                >
                  {selectedBooking.client_name} ({selectedBooking.client_number})
                </Link>
                <p className="text-slate-500">{selectedBooking.client_email} • {selectedBooking.client_phone}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl space-y-1">
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Date & Time</p>
                  <p className="font-bold text-slate-800">{formatSessionDateTime(selectedBooking.starts_at).full} UTC</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl space-y-1">
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Therapist</p>
                  <p className="font-bold text-slate-800">{selectedBooking.therapist_name}</p>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl space-y-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase">Session Classification</p>
                <div className="flex items-center gap-2 pt-1">
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${SESSION_TYPE_COLORS[selectedBooking.session_type]?.badge}`}>
                    {selectedBooking.session_type.toUpperCase()}
                  </span>
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${SESSION_MODE_CONFIG[selectedBooking.session_mode]?.badge}`}>
                    {SESSION_MODE_CONFIG[selectedBooking.session_mode]?.label}
                  </span>
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${STATUS_CONFIG[selectedBooking.status]?.badge}`}>
                    {STATUS_CONFIG[selectedBooking.status]?.label}
                  </span>
                </div>
              </div>

              {selectedBooking.virtual_meeting_link && (
                <div className="p-3 bg-cyan-50 border border-cyan-200 rounded-xl">
                  <p className="text-[10px] font-bold text-cyan-800 uppercase">Virtual Meeting URL</p>
                  <a href={selectedBooking.virtual_meeting_link} target="_blank" rel="noreferrer" className="text-xs text-cyan-700 font-semibold hover:underline break-all">
                    {selectedBooking.virtual_meeting_link}
                  </a>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <Link
                to={`/admin/crm/clients/${selectedBooking.client_id}`}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow"
              >
                Open Client Profile
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminCalendar;
