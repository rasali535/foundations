import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAdminAuth } from '../AdminAuthContext';
import { Lock, User, ShieldCheck, ArrowRight, AlertCircle, Sparkles } from 'lucide-react';

const AdminLogin = () => {
  const { login, user } = useAdminAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('adminpass123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // If already logged in, redirect
  React.useEffect(() => {
    if (user) {
      const target = location.state?.from?.pathname || '/admin/dashboard';
      navigate(target, { replace: true });
    }
  }, [user, navigate, location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      const target = location.state?.from?.pathname || '/admin/dashboard';
      navigate(target, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid staff username or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoRole = (u, p) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white font-black text-2xl shadow-xl shadow-emerald-950 mb-4">
          FCA
        </div>
        <h2 className="text-2xl font-extrabold text-white tracking-tight">
          Staff & Admin Portal
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Foundations Counselling & Advisory • Pameltex Psychosocial Services
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-slate-800/90 backdrop-blur border border-slate-700/80 py-8 px-6 sm:px-8 rounded-2xl shadow-2xl">
          {error && (
            <div className="mb-6 p-3.5 bg-rose-950/60 border border-rose-800/60 rounded-xl flex items-start gap-2.5 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Staff Username / User ID
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. admin, staff_user"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-sm rounded-xl transition shadow-lg shadow-emerald-950 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>Sign In to CRM Portal</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Role Helper Presets for testing */}
          <div className="mt-6 pt-6 border-t border-slate-700/60">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Authorized Role Quick Select (Dev/Staging)</span>
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setDemoRole('admin', 'adminpass123')}
                className="p-2 bg-slate-900/60 hover:bg-slate-700/60 border border-slate-700 rounded-lg text-left text-slate-300 transition"
              >
                <div className="font-semibold text-white">Operations Admin</div>
                <div className="text-[10px] text-slate-400">admin / adminpass123</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('clinical_lead', 'clinicalsecure2026')}
                className="p-2 bg-slate-900/60 hover:bg-slate-700/60 border border-slate-700 rounded-lg text-left text-slate-300 transition"
              >
                <div className="font-semibold text-emerald-300">Clinical Lead</div>
                <div className="text-[10px] text-slate-400">Caroline Sithole</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('staff_user', 'staffpass123')}
                className="p-2 bg-slate-900/60 hover:bg-slate-700/60 border border-slate-700 rounded-lg text-left text-slate-300 transition"
              >
                <div className="font-semibold text-blue-300">Staff Coordinator</div>
                <div className="text-[10px] text-slate-400">staff_user / staffpass123</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('therapist_kagiso', 'kagisopass123')}
                className="p-2 bg-slate-900/60 hover:bg-slate-700/60 border border-slate-700 rounded-lg text-left text-slate-300 transition"
              >
                <div className="font-semibold text-amber-300">Therapist</div>
                <div className="text-[10px] text-slate-400">Kagiso Moeti</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
