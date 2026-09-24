import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useHRAuth } from './HRAuthContext';
import InstallPortalButton from '../components/InstallPortalButton';
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
  Lock,
  Receipt,
  ReceiptText,
  ChevronRight,
  ExternalLink
} from 'lucide-react';

const HRLayout = () => {
  const { user, loading, logout, organisations, organisationId, selectOrganisation } = useHRAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400 font-medium">Verifying FCA Corporate Session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 text-center">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">Corporate HR Access Required</h2>
          <p className="text-sm text-slate-600 mt-2">
            Sign in with your Foundations corporate wellness credentials to access your organisation's secure portal.
          </p>
          <button
            onClick={() => navigate('/hr/login', { state: { from: location } })}
            className="mt-6 w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors shadow"
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
    { label: 'Aggregate Reports', path: '/hr/reports', icon: BarChart3 },
    { label: 'Booking Ledger', path: '/hr/booking-ledger', icon: ReceiptText, roles: ['hr_admin', 'super_admin', 'admin'] },
    { label: 'Invoices', path: '/hr/invoices', icon: Receipt }
  ];

  const visibleNavItems = navItems.filter((item) => !item.roles || item.roles.includes(user.role));

  const handleLogout = async () => {
    await logout();
    navigate('/hr/login');
  };

  const getRoleBadge = (role) => {
    if (role === 'hr_admin') {
      return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-100 text-emerald-800 border border-emerald-200">HR Admin</span>;
    }
    if (role === 'super_admin') {
      return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-purple-100 text-purple-800 border border-purple-200">Super Admin</span>;
    }
    if (role === 'admin') {
      return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-blue-100 text-blue-800 border border-blue-200">Operations Admin</span>;
    }
    return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-100 text-slate-700 border border-slate-200">HR Viewer</span>;
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="hidden lg:flex flex-col w-64 bg-slate-900 text-slate-300 border-r border-slate-800 shrink-0">
        <div className="p-5 border-b border-slate-800 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center text-white font-black text-lg shadow-md shadow-emerald-900/40">
            F
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">FCA Corporate Portal</h1>
            <p className="text-[11px] text-slate-400">Foundations Advisory</p>
          </div>
        </div>

        <div className="mx-4 mt-4 p-3 rounded-xl bg-slate-800/70 border border-slate-700">
          <div className="flex items-start gap-2.5">
            <Building2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Organisation</p>
              <p className="text-xs font-semibold text-white truncate mt-0.5">{user.organisation_name || 'Corporate Partner'}</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Corporate Navigation
          </div>
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-emerald-400" />}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-slate-700 text-slate-200 flex items-center justify-center font-bold text-xs">
              {user.name ? user.name.charAt(0) : 'H'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">{user.name || user.user_id}</p>
              <div className="mt-0.5">{getRoleBadge(user.role)}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/"
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Public Site</span>
            </a>
            <button
              onClick={handleLogout}
              className="flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium text-rose-300 hover:text-white bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/40 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="relative flex flex-col w-72 max-w-[80%] bg-slate-900 text-slate-300 p-4 border-r border-slate-800">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white font-bold flex items-center justify-center">F</div>
                <div>
                  <span className="font-bold text-white text-sm block">FCA Corporate</span>
                  <span className="text-[10px] text-slate-400">{user.organisation_name || 'Corporate Partner'}</span>
                </div>
              </div>
              <button onClick={() => setMobileOpen(false)} className="p-1.5 text-slate-400 hover:text-white rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex-1 py-4 space-y-1">
              {visibleNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium ${
                      isActive ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30' : 'text-slate-400'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-rose-900/40 text-rose-300 text-sm font-medium"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="hidden md:block">
              <InstallPortalButton label="Install HR Portal" />
            </div>
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-slate-800 capitalize">
                {location.pathname.split('/')[2]?.replace('-', ' ') || 'Corporate Portal'}
              </h2>
              <p className="text-[11px] text-slate-400 hidden sm:block">Foundations Counselling & Advisory</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user.role === 'super_admin' ? (
              <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                <Building2 className="w-3.5 h-3.5 text-emerald-600" />
                <select
                  value={organisationId || ''}
                  onChange={(e) => selectOrganisation(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-slate-700 outline-none max-w-52"
                  aria-label="Select organisation to inspect"
                >
                  {organisations.length === 0 ? (
                    <option value="">No organisations</option>
                  ) : (
                    organisations.map((org) => (
                      <option key={org.id} value={org.id}>{org.name}</option>
                    ))
                  )}
                </select>
              </div>
            ) : (
              <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                <Building2 className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-xs font-semibold text-slate-700 max-w-48 truncate">
                  {user.organisation_name || 'Corporate Partner'}
                </span>
              </div>
            )}
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-xs text-slate-500">Operating in:</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                CAT (UTC+2)
              </span>
            </div>
            <div className="h-4 w-px bg-slate-200 hidden sm:block"></div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-700 hidden xl:inline">{user.name}</span>
              {getRoleBadge(user.role)}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {user.role === 'super_admin' && !organisationId ? (
            <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-sm p-8 text-center">
              <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h2 className="text-lg font-bold text-slate-900">No organisation selected</h2>
              <p className="text-sm text-slate-500 mt-2">
                Add a corporate organisation from the Foundations admin portal first. Once an organisation exists, select it here to inspect its HR dashboard securely.
              </p>
            </div>
          ) : (
            <Outlet key={organisationId || user.organisation_id || 'hr-scope'} />
          )}
        </main>

        <footer className="bg-white border-t border-slate-200 py-3 px-4 sm:px-6 text-[10px] sm:text-[11px] text-slate-500">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-emerald-700 font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>FCA Confidential Corporate Reporting</span>
            </div>
            <p className="text-slate-400 text-center sm:text-right">
              Accounts visibility is restricted; clinical and employee identity data remain protected.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default HRLayout;
