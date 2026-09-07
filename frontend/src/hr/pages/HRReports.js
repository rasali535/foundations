import React, { useState, useEffect, useCallback } from 'react';
import { hrApi, useHRAuth } from '../HRAuthContext';
import {
  BarChart3,
  Download,
  Calendar,
  FileSpreadsheet,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';

const HRReports = () => {
  const { user } = useHRAuth();
  const [reportPeriod, setReportPeriod] = useState('current_month');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await hrApi.get(`/hr/dashboard?period=${reportPeriod}`);
      setReportData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setLoading(false);
    }
  }, [reportPeriod]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const res = await hrApi.get('/hr/export/csv', { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fca_wellness_aggregate_report_${reportPeriod}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to export aggregate CSV report.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider block">
            Executive Reporting
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            Corporate Wellness Utilisation Report
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Privacy-safe executive reports ready for internal leadership briefings
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          disabled={exporting}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold rounded-xl shadow transition disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <span>{exporting ? 'Generating CSV...' : 'Export Safe Aggregate CSV'}</span>
        </button>
      </div>

      {/* Filter Row */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { key: 'current_month', label: 'Current Month' },
          { key: 'previous_month', label: 'Previous Month' },
          { key: 'quarter', label: 'Current Quarter' },
          { key: 'year', label: 'Full Year' }
        ].map((p) => (
          <button
            key={p.key}
            onClick={() => setReportPeriod(p.key)}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition ${
              reportPeriod === p.key
                ? 'bg-teal-700 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-500 font-medium">Generating executive report...</p>
        </div>
      ) : error || !reportData ? (
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error || 'Unable to generate report.'}</span>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-slate-900 text-base">{reportData.organisation_name}</h3>
              <p className="text-xs text-slate-500">Report Scope: {reportData.period}</p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-lg border border-emerald-200">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Zero Client Identifiers Exported</span>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="space-y-3">
            <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider text-slate-500">
              Attendance & Operational Metrics
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-semibold">Total Sessions</span>
                <span className="text-xl font-black text-slate-900 mt-1 block">
                  {reportData.total_sessions.display}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-semibold">Completed</span>
                <span className="text-xl font-black text-emerald-700 mt-1 block">
                  {reportData.completed.display}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-semibold">Cancelled</span>
                <span className="text-xl font-black text-amber-700 mt-1 block">
                  {reportData.cancelled.display}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-semibold">No-Shows</span>
                <span className="text-xl font-black text-rose-700 mt-1 block">
                  {reportData.no_show.display}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider text-slate-500">
              Session Distribution By Modality & Type
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-50 rounded-xl space-y-2">
                <span className="font-bold text-slate-700 block">Session Types</span>
                <div className="space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Individual:</span>
                    <strong className="text-slate-900">{reportData.session_types.individual?.display}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Couple Therapy:</span>
                    <strong className="text-slate-900">{reportData.session_types.couple?.display}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Family Systems:</span>
                    <strong className="text-slate-900">{reportData.session_types.family?.display}</strong>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl space-y-2">
                <span className="font-bold text-slate-700 block">Delivery Modality</span>
                <div className="space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>In-Person Consultations:</span>
                    <strong className="text-slate-900">{reportData.session_modes.in_person?.display}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Virtual Video Sessions:</span>
                    <strong className="text-slate-900">{reportData.session_modes.virtual?.display}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Footnote */}
          <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Foundations Counselling & Advisory • Protected Corporate HR Reporting</span>
            <span>All values &lt;5 suppressed by privacy protocol</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default HRReports;
