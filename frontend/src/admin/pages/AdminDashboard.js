import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../AdminAuthContext';
import {
  Users,
  FileText,
  Calendar,
  Clock,
  AlertTriangle,
  UserX,
  PlusCircle,
  CalendarPlus,
  ArrowUpRight,
  Video,
  Building2,
  CheckCircle2,
  Activity,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { SESSION_TYPE_COLORS, SESSION_MODE_CONFIG, STATUS_CONFIG, formatSessionDateTime } from '../AdminConstants';

const AdminDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await api.get('/crm/dashboard');
      setData(res.data);
    } catch (err) {
      setError('Failed to load operational dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="py-12 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm text-slate-500">Loading operational KPIs & schedule...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
        {error || 'Dashboard data unavailable.'}
      </div>
    );
  }

  const { kpis, today_bookings, recent_clients, recent_intakes, recent_activity } = data;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">Operational Overview</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Foundations Counselling & Advisory CRM • Real-time clinical and appointment telemetry
          </p>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/admin/crm/clients"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition"
          >
            <Users className="w-4 h-4" />
            <span>Clients Directory</span>
          </Link>
          <Link
            to="/admin/bookings"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow transition"
          >
            <CalendarPlus className="w-4 h-4" />
            <span>Manage Bookings</span>
          </Link>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Total Clients */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Clients</span>
            <Users className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.total_clients}</p>
          <span className="text-[10px] text-slate-400">Registered CRM Profiles</span>
        </div>

        {/* Intakes */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Intake Submissions</span>
            <FileText className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.total_intakes}</p>
          <span className="text-[10px] text-slate-400">Total Website Forms</span>
        </div>

        {/* Today's Appointments */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Today's Sessions</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.today_appointments_count}</p>
          <span className="text-[10px] text-amber-600 font-medium">Scheduled for today</span>
        </div>

        {/* Upcoming Appointments */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Next 7 Days</span>
            <Calendar className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.upcoming_appointments_count}</p>
          <span className="text-[10px] text-slate-400">Confirmed sessions</span>
        </div>

        {/* Cancellations */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Cancellations</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.cancellations_count}</p>
          <span className="text-[10px] text-slate-400">Retained in history</span>
        </div>

        {/* No-Shows */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">No-Shows</span>
            <UserX className="w-4 h-4 text-slate-500" />
          </div>
          <p className="text-2xl font-black text-slate-800 mt-2">{kpis.no_show_count}</p>
          <span className="text-[10px] text-slate-400">Tracked for follow-up</span>
        </div>
      </div>

      {/* Main Grid: Today's Schedule + Feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Today's Schedule */}
        <div className="lg:col-span-2 space-y-6">
          {/* Today's Schedule Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <h3 className="font-bold text-slate-900 text-sm sm:text-base">Today's Appointment Schedule</h3>
              </div>
              <Link to="/admin/calendar" className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1">
                <span>View Full Calendar</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="divide-y divide-slate-100">
              {today_bookings.length === 0 ? (
                <div className="p-8 text-center">
                  <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-medium text-slate-600">No appointments scheduled for today.</p>
                  <p className="text-xs text-slate-400 mt-0.5">Use the bookings page to schedule upcoming consultations.</p>
                </div>
              ) : (
                today_bookings.map((booking) => {
                  const typeConf = SESSION_TYPE_COLORS[booking.session_type] || SESSION_TYPE_COLORS.individual;
                  const modeConf = SESSION_MODE_CONFIG[booking.session_mode] || SESSION_MODE_CONFIG.in_person;
                  const statusConf = STATUS_CONFIG[booking.status] || STATUS_CONFIG.confirmed;
                  const dt = formatSessionDateTime(booking.starts_at);

                  return (
                    <div key={booking.id} className="p-4 hover:bg-slate-50/80 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-start gap-3.5">
                        <div className="flex flex-col items-center justify-center w-14 h-14 bg-slate-100 border border-slate-200 rounded-xl text-slate-800 shrink-0">
                          <span className="text-xs font-bold text-slate-900">{dt.time}</span>
                          <span className="text-[10px] text-slate-500">UTC</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 text-sm">{booking.client_name}</span>
                            <span className="text-xs text-slate-400">({booking.client_number})</span>
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Therapist: <strong className="text-slate-700">{booking.therapist_name}</strong>
                          </p>
                          <div className="flex flex-wrap items-center gap-1.5 mt-2">
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${typeConf.badge}`}>
                              {typeConf.label}
                            </span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${modeConf.badge} flex items-center gap-1`}>
                              {booking.session_mode === 'virtual' ? <Video className="w-3 h-3" /> : <Building2 className="w-3 h-3" />}
                              <span>{modeConf.label}</span>
                            </span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${statusConf.badge}`}>
                              {statusConf.label}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <Link
                          to={`/admin/crm/clients/${booking.client_id}`}
                          className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg transition"
                        >
                          Client Profile
                        </Link>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Recent Intakes Section */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-600" />
                <span>Recent Intake Submissions</span>
              </h3>
              <Link to="/admin/crm/clients" className="text-xs font-semibold text-emerald-600 hover:text-emerald-700">
                View All Clients
              </Link>
            </div>
            <div className="space-y-3">
              {recent_intakes.map((intake) => {
                const sub = intake.submission_data || {};
                const name = sub.full_name || sub.name || 'Client';
                const dt = formatSessionDateTime(intake.created_at);
                const isHighRisk = intake.is_high_risk;

                return (
                  <div key={intake.id} className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-slate-900">{name}</span>
                        {isHighRisk ? (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
                            High Priority Triage
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                            Routine Counselling
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 truncate max-w-sm">
                        Reason: {sub.reason_for_seeking_therapy || sub.reason || 'General Counselling'}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-[10px] text-slate-400 block">{dt.date}</span>
                      <Link
                        to={`/admin/crm/clients/${intake.client_id}`}
                        className="text-[11px] font-semibold text-emerald-600 hover:underline"
                      >
                        Open Profile →
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right 1 Col: Recent Clients & Activity Stream */}
        <div className="space-y-6">
          {/* Recent Clients */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-600" />
                <span>Recently Registered Clients</span>
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {recent_clients.map((client) => (
                <div key={client.id} className="py-2.5 flex items-center justify-between">
                  <div>
                    <Link
                      to={`/admin/crm/clients/${client.id}`}
                      className="text-xs font-bold text-slate-900 hover:text-emerald-600 transition"
                    >
                      {client.first_name} {client.last_name}
                    </Link>
                    <p className="text-[11px] text-slate-400">{client.client_number} • {client.email}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-300" />
                </div>
              ))}
            </div>
          </div>

          {/* Activity Stream */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-600" />
                <span>Audit & Activity Stream</span>
              </h3>
            </div>
            <div className="space-y-3">
              {recent_activity.map((act) => {
                const dt = formatSessionDateTime(act.created_at);
                return (
                  <div key={act.id} className="text-xs border-l-2 border-slate-200 pl-3 py-0.5">
                    <p className="font-semibold text-slate-800 capitalize">
                      {act.action.replace(/_/g, ' ')}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {dt.date} {dt.time} • By {act.actor_name || 'System / Client'}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
