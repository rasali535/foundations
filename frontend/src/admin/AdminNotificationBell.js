import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Volume2, VolumeX } from 'lucide-react';
import { api } from './AdminAuthContext';

const labels = {
  admin_intake_received: 'New intake received',
  admin_booking_pending: 'Booking awaiting therapist allocation',
  admin_booking_declined: 'Therapist declined — allocation needed',
};

export default function AdminNotificationBell() {
  const [data, setData] = useState({ alerts: [], unread: 0, failures: 0 });
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const [sound, setSound] = useState(false);
  const seen = useRef(null);
  const audio = useRef(null);
  const refresh = useCallback(async () => {
    try {
      const result = await api.get('/admin-ops/alerts');
      const next = result.data;
      if (sound && seen.current && next.alerts.some(a => !seen.current.has(a.event_key)) && audio.current) {
        const ctx = audio.current;
        if (ctx.state === 'running') {
          const oscillator = ctx.createOscillator();
          const gain = ctx.createGain();
          gain.gain.setValueAtTime(0.06, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
          oscillator.connect(gain); gain.connect(ctx.destination);
          oscillator.frequency.value = 660; oscillator.start(); oscillator.stop(ctx.currentTime + 0.2);
        }
      }
      seen.current = new Set(next.alerts.map(a => a.event_key));
      setData(next); setError('');
    } catch { setError('Alerts could not be refreshed.'); }
  }, [sound]);
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 30000);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => () => { audio.current?.close(); }, []);
  const toggleSound = async () => {
    if (!sound) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      try { audio.current = audio.current || new AudioContext(); await audio.current.resume(); }
      catch { setError('Sound is unavailable on this device.'); return; }
    }
    setSound(!sound);
  };
  const acknowledge = async (eventKeys) => {
    try { await api.post('/admin-ops/alerts/read', { event_keys: eventKeys }); await refresh(); }
    catch { setError('Could not mark the alert as read.'); }
  };
  return <div className="relative">
    <button aria-label={`Notifications: ${data.unread} unread`} aria-expanded={open}
      onClick={() => setOpen(!open)} className="relative p-2 rounded-lg hover:bg-slate-100">
      <Bell className="w-5 h-5" />
      {data.unread > 0 && <span className="absolute -top-1 -right-1 bg-emerald-700 text-white rounded-full px-1 text-xs">{data.unread > 99 ? '99+' : data.unread}</span>}
    </button>
    {open && <div className="absolute right-0 mt-3 w-80 max-w-[85vw] bg-white rounded-xl border shadow-xl z-40 p-4">
      <div className="flex justify-between items-center mb-3"><strong>Notifications</strong>
        <button onClick={toggleSound} aria-label={sound ? 'Mute alert sound' : 'Enable alert sound'}>{sound ? <Volume2 size={18} /> : <VolumeX size={18} />}</button>
      </div>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      {data.failures > 0 && <Link to="/admin/settings" onClick={() => setOpen(false)} className="block text-sm text-rose-700 mb-3">{data.failures} notifications need attention</Link>}
      <div className="max-h-80 overflow-y-auto space-y-3">
        {data.alerts.length === 0 && <p className="text-sm text-slate-500">No unread alerts.</p>}
        {data.alerts.map(alert => <div key={alert.event_key} className="border-b pb-2 text-sm">
          <Link to={alert.url} onClick={() => { acknowledge([alert.event_key]); setOpen(false); }} className="font-medium text-emerald-800">{labels[alert.event] || 'New operational alert'}</Link>
          <p className="text-xs text-slate-500 mt-1">{new Date(alert.created_at).toLocaleString('en-GB', { timeZone: 'Africa/Gaborone' })} CAT</p>
          <button onClick={() => acknowledge([alert.event_key])} className="text-xs text-slate-600 mt-1">Mark as read</button>
        </div>)}
      </div>
    </div>}
  </div>;
}
