import React, { useEffect, useMemo, useState } from 'react';
import { Eye, EyeOff, KeyRound, ShieldCheck, LockKeyhole, History, CheckCircle2, AlertCircle } from 'lucide-react';
import { hrApi, useHRAuth } from '../HRAuthContext';

const activityIcon = (action) => {
  if (action === 'hr_password_changed') return KeyRound;
  return History;
};

const HRAccountSecurity = () => {
  const { user } = useHRAuth();
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [show, setShow] = useState({
    current: false,
    next: false,
    confirm: false
  });
  const [activity, setActivity] = useState([]);
  const [activityLoading, setActivityLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const rules = useMemo(() => ({
    length: form.new_password.length >= 12,
    upper: /[A-Z]/.test(form.new_password),
    lower: /[a-z]/.test(form.new_password),
    number: /\d/.test(form.new_password),
    symbol: /[^A-Za-z0-9]/.test(form.new_password),
    match: form.new_password.length > 0 && form.new_password === form.confirm_password
  }), [form.new_password, form.confirm_password]);

  const ready = Object.values(rules).every(Boolean) && form.current_password.length > 0;

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await hrApi.get('/hr/account/activity');
        if (mounted) setActivity(res.data?.activity || []);
      } catch (err) {
        if (mounted) setActivity([]);
      } finally {
        if (mounted) setActivityLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setError('');
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!ready || saving) return;

    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const res = await hrApi.post('/hr/account/change-password', form);
      if (res.data?.status === 'password_changed') {
        setSuccess('Password changed successfully. For your security, all previous HR sessions have been signed out.');
        setForm({ current_password: '', new_password: '', confirm_password: '' });
        window.setTimeout(() => {
          window.location.assign('/hr/login');
        }, 1800);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Password could not be changed. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const Rule = ({ ok, children }) => (
    <div className={`flex items-center gap-2 text-xs ${ok ? 'text-emerald-700' : 'text-slate-500'}`}>
      <CheckCircle2 className={`w-3.5 h-3.5 ${ok ? 'text-emerald-600' : 'text-slate-300'}`} />
      <span>{children}</span>
    </div>
  );

  const PasswordInput = ({ label, value, field, visibleKey, autoComplete }) => (
    <label className="block">
      <span className="block text-xs font-semibold text-slate-700 mb-1.5">{label}</span>
      <div className="relative">
        <input
          type={show[visibleKey] ? 'text' : 'password'}
          value={value}
          onChange={update(field)}
          autoComplete={autoComplete}
          className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 pr-11 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
        />
        <button
          type="button"
          onClick={() => setShow((current) => ({ ...current, [visibleKey]: !current[visibleKey] }))}
          className="absolute inset-y-0 right-0 px-3 text-slate-400 hover:text-slate-700"
          aria-label={show[visibleKey] ? 'Hide password' : 'Show password'}
        >
          {show[visibleKey] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </label>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 text-emerald-700 mb-1">
          <ShieldCheck className="w-5 h-5" />
          <span className="text-xs font-bold uppercase tracking-wider">Account Security</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">My Account & Security</h1>
        <p className="text-sm text-slate-500 mt-1">
          Control your own HR portal password and review security-relevant activity for your account.
        </p>
      </div>

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-xl bg-white border border-emerald-200 flex items-center justify-center shrink-0">
            <LockKeyhole className="w-5 h-5 text-emerald-700" />
          </div>
          <div>
            <h2 className="font-bold text-emerald-950">Your password is private</h2>
            <p className="text-sm leading-6 text-emerald-900/80 mt-1">
              Your password is stored only as a secure one-way hash and cannot be viewed by Foundations staff.
              Administrative and HR portal actions are logged for accountability.
            </p>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-6">
        <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-5">
            <KeyRound className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="font-bold text-slate-900">Change password</h2>
              <p className="text-xs text-slate-500 mt-0.5">Signed in as {user?.name || user?.user_id}</p>
            </div>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <PasswordInput
              label="Current password"
              value={form.current_password}
              field="current_password"
              visibleKey="current"
              autoComplete="current-password"
            />
            <PasswordInput
              label="New password"
              value={form.new_password}
              field="new_password"
              visibleKey="next"
              autoComplete="new-password"
            />
            <PasswordInput
              label="Confirm new password"
              value={form.confirm_password}
              field="confirm_password"
              visibleKey="confirm"
              autoComplete="new-password"
            />

            <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5 grid sm:grid-cols-2 gap-2">
              <Rule ok={rules.length}>At least 12 characters</Rule>
              <Rule ok={rules.upper}>One uppercase letter</Rule>
              <Rule ok={rules.lower}>One lowercase letter</Rule>
              <Rule ok={rules.number}>One number</Rule>
              <Rule ok={rules.symbol}>One symbol</Rule>
              <Rule ok={rules.match}>Passwords match</Rule>
            </div>

            {error && (
              <div className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-sm text-rose-800">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="flex gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-sm text-emerald-800">
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{success}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!ready || saving}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <KeyRound className="w-4 h-4" />
              {saving ? 'Changing password…' : 'Change password'}
            </button>

            <p className="text-[11px] leading-5 text-slate-500">
              Changing your password signs out every existing HR portal session, including this one. You will need to sign in again with the new password.
            </p>
          </form>
        </section>

        <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-5">
            <History className="w-5 h-5 text-slate-600" />
            <div>
              <h2 className="font-bold text-slate-900">Account activity</h2>
              <p className="text-xs text-slate-500 mt-0.5">Your recent HR portal actions</p>
            </div>
          </div>

          {activityLoading ? (
            <div className="py-10 text-center text-sm text-slate-400">Loading account activity…</div>
          ) : activity.length === 0 ? (
            <div className="py-10 text-center">
              <History className="w-8 h-8 text-slate-200 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-600">No recent activity recorded yet.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {activity.map((item, index) => {
                const Icon = activityIcon(item.action);
                const timestamp = item.created_at ? new Date(item.created_at) : null;
                return (
                  <div key={`${item.action}-${item.created_at}-${index}`} className="py-3 flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-slate-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800">{item.label}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {timestamp && !Number.isNaN(timestamp.getTime())
                          ? timestamp.toLocaleString()
                          : 'Time unavailable'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default HRAccountSecurity;
