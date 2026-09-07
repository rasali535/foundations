import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useHRAuth } from './HRAuthContext';
import {
  LayoutDashboard,
  FileCheck2,
  TrendingUp,
  BarChart3,
  LogOut,
  Building2,
  ShieldCheck,
  Menu,
  X,
  Lock
} from 'lucide-react';

const HRLayout = () => {
  const { user, loading, logout } = useHRAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400 font-medium">Verifying Corporate Portal Session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 text-center">
          <div className="w-12 h-12 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-black text-slate-900">Corporate HR Access Required</h2>
          <p className="text-xs text-slate-600 mt-2 leading-relaxed">
            Please log in with your corporate wellness administrator credentials to access your organisation's aggregate utilisation reports.
          </p>
          <button
            onClick={() => navigate('/hr/login', { state: { from: location } })}
            className="mt-6 w-full py-2.5 px-4 bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold rounded-xl transition shadow"
          >
            Go to Corporate HR Login
          </button>
        </div>
      </div>
    );
  }

  const navItems = [
    { label: 'Dashboard', path: '/hr/dashboard', icon: LayoutDashboard },
    { label: 'Contract Overview', path: '/hr/contract', icon: FileCheck2 },
    { label: 'Utilisation Trends', path: '/hr/utilisation', icon: TrendingUp },
    { label: 'Aggregate Reports', path: '/hr/reports', icon: BarChart3 }
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/hr/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo & Portal Branding */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-teal-700 to-emerald-600 text-white flex items-center justify-center font-black shadow-md">
                FCA
              </div>
              <div>
                <span className="text-xs font-black tracking-wider text-teal-800 uppercase block leading-none">
                  Foundations Counselling & Advisory
                </span>
                <span className="text-xs text-slate-500 font-bold">
                  Corporate Wellness Portal
                </span>
              </div>
            </div>

            {/* Organisation Badge & User */}
            <div className="hidden md:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-xs">
                <Building2 className="w-4 h-4 text-teal-700 shrink-0" />
                <span className="font-bold text-slate-800">{user.organisation_name}</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-teal-100 text-teal-800 uppercase">
                  {user.role === 'hr_admin' ? 'HR Admin' : 'HR Viewer'}
                </span>
              </div>

              <div className="text-right">
                <span className="text-xs font-bold text-slate-900 block">{user.name}</span>
                <span className="text-[10px] text-slate-400 block">{user.user_id}</span>
              </div>

              <button
                onClick={handleLogout}
                className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition"
                title="Sign out of Corporate Portal"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>

            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 text-slate-600 rounded-lg hover:bg-slate-100"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Desktop Navigation Row */}
        <div className="hidden md:block bg-slate-50/80 border-t border-slate-100 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto flex items-center gap-1 py-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all ${
                      isActive
                        ? 'bg-teal-700 text-white shadow-sm'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileOpen && (
          <div className="md:hidden p-4 bg-white border-t border-slate-200 space-y-3">
            <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 text-xs">
              <Building2 className="w-4 h-4 text-teal-700" />
              <span className="font-bold text-slate-800">{user.organisation_name}</span>
            </div>
            <div className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2 text-xs font-bold rounded-lg ${
                        isActive ? 'bg-teal-700 text-white' : 'text-slate-700 hover:bg-slate-100'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
            <button
              onClick={handleLogout}
              className="w-full mt-2 py-2 px-3 flex items-center justify-center gap-2 text-xs font-bold text-rose-600 bg-rose-50 rounded-lg hover:bg-rose-100"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>

      {/* Confidentiality & Privacy Notice Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-6 text-center text-[11px] text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-emerald-700 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>FCA Clinical Confidentiality & Anonymity Guarantee</span>
          </div>
          <p className="text-slate-400">
            Strict aggregate-only reporting. Personal identities, clinical assessments, intake answers, and individual appointments are never disclosed.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HRLayout;
