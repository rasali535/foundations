import React, { useState, useEffect } from 'react';
import { hrApi, useHRAuth } from '../HRAuthContext';
import {
  FileCheck2,
  Calendar,
  Layers,
  PieChart,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

const HRContract = () => {
  const { user } = useHRAuth();
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchContract = async () => {
      setLoading(true);
      try {
        const res = await hrApi.get('/hr/contract');
        setContract(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load contract information.');
      } finally {
        setLoading(false);
      }
    };
    fetchContract();
  }, []);

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Loading contract overview...</p>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs flex items-center gap-3">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>{error || 'Unable to retrieve contract details.'}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider block">
            Advisory Agreement Overview
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            {contract.organisation_name}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Corporate Mental Health & Advisory Services Contract
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
            contract.contract_status === 'active'
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              : 'bg-slate-100 text-slate-600 border border-slate-300'
          }`}>
            Status: {contract.contract_status}
          </span>
        </div>
      </div>

      {/* Contract Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 block">Total Allocated Pool</span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-black text-slate-900">
              {contract.allocated_sessions != null ? contract.allocated_sessions : 'Not configured'}
            </span>
            <span className="text-xs text-slate-400">sessions</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Contractual annual allocation</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 block">Sessions Utilised</span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-black text-teal-700">
              {contract.sessions_used}
            </span>
            <span className="text-xs text-slate-400">sessions</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Completed & confirmed sessions</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 block">Sessions Remaining</span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-black text-slate-900">
              {contract.sessions_remaining != null ? contract.sessions_remaining : 'N/A'}
            </span>
            <span className="text-xs text-slate-400">sessions</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Available balance in pool</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 block">Utilisation Rate</span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-black text-emerald-700">
              {contract.utilisation_percentage != null ? `${contract.utilisation_percentage}%` : 'N/A'}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Percentage of pool consumed</p>
        </div>
      </div>

      {/* Contract Terms & Progress Details */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm space-y-6">
        <div>
          <h3 className="font-bold text-slate-900 text-sm mb-1">Contract Progress & Allocation</h3>
          <p className="text-xs text-slate-500">
            Real-time track of your corporate counselling allocation under the master agreement.
          </p>
        </div>

        {contract.utilisation_percentage != null && (
          <div className="space-y-2 p-4 bg-slate-50 rounded-xl">
            <div className="flex justify-between text-xs font-bold text-slate-700">
              <span>Pool Utilisation Gauge</span>
              <span>{contract.sessions_used} of {contract.allocated_sessions} Sessions ({contract.utilisation_percentage}%)</span>
            </div>
            <div className="w-full h-3.5 bg-slate-200 rounded-full overflow-hidden p-0.5">
              <div
                className="h-full bg-gradient-to-r from-teal-500 to-emerald-600 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(contract.utilisation_percentage, 100)}%` }}
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-slate-50 rounded-xl space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">Agreement Period</span>
            <div className="flex items-center gap-2 text-slate-900 font-semibold">
              <Calendar className="w-4 h-4 text-teal-600" />
              <span>
                {contract.contract_start && contract.contract_end
                  ? `${contract.contract_start} to ${contract.contract_end}`
                  : 'Multi-year Ongoing Advisory Framework'}
              </span>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">Contract Accounting Rule</span>
            <div className="flex items-center gap-2 text-slate-900 font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Deductions occur on session completion or confirmed booking</span>
            </div>
          </div>
        </div>
      </div>

      {/* Confidentiality Callout */}
      <div className="p-4 bg-teal-50/60 border border-teal-200/70 rounded-2xl flex items-start gap-3 text-xs text-teal-900">
        <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div>
          <strong className="block font-bold">Privacy Architecture:</strong>
          <p className="text-teal-800/90 mt-0.5 leading-relaxed">
            All utilisation figures are computed strictly at the organisational level. FCA will never disclose employee names, departments, or individual booking records to HR or corporate sponsors.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HRContract;
