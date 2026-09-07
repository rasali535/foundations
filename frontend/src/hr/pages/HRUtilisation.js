import React, { useState, useEffect } from 'react';
import { hrApi, useHRAuth } from '../HRAuthContext';
import { TrendingUp, AlertCircle, ShieldCheck, BarChart2 } from 'lucide-react';

const HRUtilisation = () => {
  const { user } = useHRAuth();
  const [trendsData, setTrendsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTrends = async () => {
      setLoading(true);
      try {
        const res = await hrApi.get('/hr/utilisation?granularity=monthly');
        setTrendsData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load utilisation trend history.');
      } finally {
        setLoading(false);
      }
    };
    fetchTrends();
  }, []);

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Computing historical utilisation trends...</p>
      </div>
    );
  }

  if (error || !trendsData) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs flex items-center gap-3">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>{error || 'Unable to retrieve trend analytics.'}</span>
      </div>
    );
  }

  const { trends, organisation_name, privacy_notice } = trendsData;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Title */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider block">
            Longitudinal Analytics
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            Utilisation Trends & Trajectory
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            {organisation_name} • Monthly aggregate session engagement
          </p>
        </div>
      </div>

      {/* Visual Bar Graph of Trends */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Monthly Session Volume</h3>
            <span className="text-[11px] text-slate-400">Aggregate session load over time</span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 rounded-lg text-slate-600">
            Granularity: Monthly
          </span>
        </div>

        {trends.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No historical session records found for this organisation yet.
          </div>
        ) : (
          <div className="space-y-4 pt-2">
            {trends.map((pt) => {
              const numericCount = pt.total_sessions.count || (pt.total_sessions.suppressed ? 4 : 0);
              const maxCount = Math.max(...trends.map(t => t.total_sessions.count || 5), 10);
              const barPercent = Math.min((numericCount / maxCount) * 100, 100);

              return (
                <div key={pt.period} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-slate-800">{pt.period}</span>
                    <div className="flex items-center gap-2">
                      {pt.total_sessions.suppressed ? (
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-[10px] font-bold">
                          Masked (&lt;5 sessions)
                        </span>
                      ) : (
                        <span className="font-black text-slate-900">{pt.total_sessions.display} sessions</span>
                      )}
                    </div>
                  </div>
                  <div className="w-full h-4 bg-slate-100 rounded-full overflow-hidden p-0.5">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        pt.total_sessions.suppressed
                          ? 'bg-amber-400 opacity-60'
                          : 'bg-teal-600'
                      }`}
                      style={{ width: `${Math.max(barPercent, 6)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Aggregate Trend Breakdown Table */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">Historical Period Breakdown</h3>
          <span className="text-[11px] text-slate-400 font-medium">Safe aggregate metrics</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
              <tr>
                <th className="py-3.5 px-5 font-bold">Period</th>
                <th className="py-3.5 px-5 font-bold">Total Sessions</th>
                <th className="py-3.5 px-5 font-bold">Completed</th>
                <th className="py-3.5 px-5 font-bold">Cancelled</th>
                <th className="py-3.5 px-5 font-bold">No-Shows</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {trends.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">
                    No trend records available.
                  </td>
                </tr>
              ) : (
                trends.map((pt) => (
                  <tr key={pt.period} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 px-5 font-bold text-slate-900">{pt.period}</td>
                    <td className="py-3.5 px-5 font-semibold">
                      <span className={pt.total_sessions.suppressed ? 'text-amber-700 font-bold' : 'text-slate-900'}>
                        {pt.total_sessions.display}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 font-semibold text-emerald-700">{pt.completed.display}</td>
                    <td className="py-3.5 px-5 font-semibold text-amber-700">{pt.cancelled.display}</td>
                    <td className="py-3.5 px-5 font-semibold text-rose-700">{pt.no_show.display}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Privacy Notice */}
      <div className="p-4 bg-teal-50/60 border border-teal-200/70 rounded-2xl flex items-start gap-3 text-xs text-teal-900">
        <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div>
          <strong className="block font-bold">Small-Count Protection:</strong>
          <p className="text-teal-800/90 mt-0.5 leading-relaxed">
            {privacy_notice} This prevents identification of individuals based on calendar activity in low-volume months.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HRUtilisation;
