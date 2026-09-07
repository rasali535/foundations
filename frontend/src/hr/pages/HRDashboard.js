import React, { useState, useEffect, useCallback } from 'react';
import { hrApi, useHRAuth } from '../HRAuthContext';
import {
  Users,
  CalendarCheck,
  CalendarX,
  UserX,
  FileCheck2,
  Video,
  Building2,
  ShieldCheck,
  AlertCircle,
  HelpCircle
} from 'lucide-react';

const HRDashboard = () => {
  const { user } = useHRAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState('current_month');

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await hrApi.get(`/hr/dashboard?period=${period}`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load corporate dashboard metrics.');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Aggregating corporate utilisation data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs flex items-center gap-3">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>{error || 'Unable to display corporate dashboard.'}</span>
      </div>
    );
  }

  const { total_sessions, completed, cancelled, no_show, session_types, session_modes, contract } = data;

  return (
    <div className="space-y-6">
      {/* Top Welcome & Period Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider block">
            Wellness Programme Engagement
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            {data.organisation_name}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Period: <strong className="text-slate-800">{data.period}</strong> • Reporting minimum threshold: 5 sessions
          </p>
        </div>

        {/* Period Selector Filter */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0">
          {[
            { key: 'current_month', label: 'Current Month' },
            { key: 'previous_month', label: 'Last Month' },
            { key: 'quarter', label: 'This Quarter' },
            { key: 'year', label: 'This Year' }
          ].map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                period === p.key
                  ? 'bg-white text-teal-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Primary Utilisation Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Sessions */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Total Utilisation</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center font-bold">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-slate-900">
              {total_sessions.display}
            </div>
            <span className="text-[11px] text-slate-400 mt-1 block">
              {total_sessions.suppressed ? 'Masked (<5 sessions)' : 'Total appointments booked'}
            </span>
          </div>
        </div>

        {/* Completed */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Sessions Completed</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
              <CalendarCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-emerald-700">
              {completed.display}
            </div>
            <span className="text-[11px] text-slate-400 mt-1 block">
              {completed.suppressed ? 'Masked (<5 sessions)' : 'Successfully attended'}
            </span>
          </div>
        </div>

        {/* Cancelled */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Cancelled</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
              <CalendarX className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-amber-700">
              {cancelled.display}
            </div>
            <span className="text-[11px] text-slate-400 mt-1 block">
              {cancelled.suppressed ? 'Masked (<5 sessions)' : 'Prior notice cancellations'}
            </span>
          </div>
        </div>

        {/* No-Shows */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">No-Shows</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center font-bold">
              <UserX className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-rose-700">
              {no_show.display}
            </div>
            <span className="text-[11px] text-slate-400 mt-1 block">
              {no_show.suppressed ? 'Masked (<5 sessions)' : 'Missed appointments'}
            </span>
          </div>
        </div>
      </div>

      {/* Contract & Modality Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contract Utilisation Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm lg:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-teal-700" />
                <h3 className="font-bold text-slate-900 text-sm">Contract Pool</h3>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                contract.contract_status === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
              }`}>
                {contract.contract_status}
              </span>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Contract Session Pool</span>
                <span className="font-black text-slate-900 text-sm">
                  {contract.allocated_sessions != null ? contract.allocated_sessions : 'Not configured'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Sessions Utilised</span>
                <span className="font-bold text-teal-700 text-sm">{contract.sessions_used}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Sessions Remaining</span>
                <span className="font-bold text-slate-800 text-sm">
                  {contract.sessions_remaining != null ? contract.sessions_remaining : 'N/A'}
                </span>
              </div>

              {contract.utilisation_percentage != null && (
                <div className="pt-2">
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 mb-1">
                    <span>Overall Pool Utilisation</span>
                    <span>{contract.utilisation_percentage}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-teal-500 to-emerald-600 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(contract.utilisation_percentage, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-slate-100 text-[11px] text-slate-400">
            {contract.contract_start && contract.contract_end
              ? `Term: ${contract.contract_start} to ${contract.contract_end}`
              : 'Annual Corporate Advisory Agreement'}
          </div>
        </div>

        {/* Session Type Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm lg:col-span-1">
          <div className="pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-sm">Session Type Distribution</h3>
            <span className="text-[11px] text-slate-400">Aggregate breakdown by appointment type</span>
          </div>

          <div className="mt-4 space-y-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Individual Counselling</span>
                <span className="text-[10px] text-slate-400">One-on-one employee sessions</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-black text-slate-900">
                  {session_types.individual?.display || '0'}
                </span>
                {session_types.individual?.suppressed && (
                  <span className="text-[9px] text-amber-600 block font-semibold">Masked</span>
                )}
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Couple Therapy</span>
                <span className="text-[10px] text-slate-400">Relationship support</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-black text-slate-900">
                  {session_types.couple?.display || '0'}
                </span>
                {session_types.couple?.suppressed && (
                  <span className="text-[9px] text-amber-600 block font-semibold">Masked</span>
                )}
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Family Systems</span>
                <span className="text-[10px] text-slate-400">Parental / family wellbeing</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-black text-slate-900">
                  {session_types.family?.display || '0'}
                </span>
                {session_types.family?.suppressed && (
                  <span className="text-[9px] text-amber-600 block font-semibold">Masked</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Session Mode Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm lg:col-span-1">
          <div className="pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-sm">Modality Breakdown</h3>
            <span className="text-[11px] text-slate-400">Delivery channel distribution</span>
          </div>

          <div className="mt-4 space-y-4 text-xs">
            <div className="p-4 bg-slate-50 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center font-bold">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block">In-Person Clinic</span>
                  <span className="text-[11px] text-slate-500">Central Clinic consultations</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-base font-black text-slate-900">
                  {session_modes.in_person?.display || '0'}
                </span>
                {session_modes.in_person?.suppressed && (
                  <span className="text-[9px] text-amber-600 block font-semibold">Masked</span>
                )}
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold">
                  <Video className="w-5 h-5" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block">Virtual Video</span>
                  <span className="text-[11px] text-slate-500">Secure digital video rooms</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-base font-black text-slate-900">
                  {session_modes.virtual?.display || '0'}
                </span>
                {session_modes.virtual?.suppressed && (
                  <span className="text-[9px] text-amber-600 block font-semibold">Masked</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Privacy Notice Banner */}
      <div className="p-4 bg-teal-50/60 border border-teal-200/70 rounded-2xl flex items-start gap-3 text-xs text-teal-900">
        <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div>
          <strong className="block font-bold">Privacy-Preserving Reporting Model:</strong>
          <p className="text-teal-800/90 mt-0.5 leading-relaxed">
            {data.privacy_notice} Individual employee records, reasons for seeking counselling, intake questionnaire answers, and therapist identities are strictly sealed and cannot be accessed from this portal.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HRDashboard;
