import React, { useCallback, useEffect, useState } from 'react';
import { api } from './AdminAuthContext';

export default function NotificationQueue() {
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin-ops/notification-queue'); setJobs(data); setError(''); }
    catch { setError('Could not load notification delivery queue.'); }
  }, []);
  useEffect(() => { load(); const timer = setInterval(load, 30000); return () => clearInterval(timer); }, [load]);
  const retry = async (eventKey) => {
    setBusy(eventKey);
    try { await api.post('/admin-ops/notification-queue/retry', { event_key: eventKey }); await load(); }
    catch { setError('Could not retry this notification. Refresh and check its status.'); }
    finally { setBusy(null); }
  };
  return <section className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3">
    <h3 className="font-bold text-slate-900">Notification delivery queue</h3>
    <p className="text-sm text-slate-600">Failed messages can be retried after correcting the number or template settings. Unknown delivery needs verification before sending again.</p>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    <div className="overflow-x-auto"><table className="w-full text-xs text-left">
      <thead><tr><th className="p-2">Notification</th><th className="p-2">Status</th><th className="p-2">Attempts</th><th className="p-2">Delivery details</th><th className="p-2">Action</th></tr></thead>
      <tbody>{jobs.map(job => <tr key={job.event_key} className="border-t">
        <td className="p-2">{job.kind.replace(/_/g, ' ')}</td>
        <td className="p-2">{job.status === 'sent' ? 'accepted by provider' : job.status.replace(/_/g, ' ')}</td>
        <td className="p-2">{job.attempts}</td>
        <td className="p-2 text-rose-700">{job.error_message || '—'}</td>
        <td className="p-2">{job.status === 'failed' && <button disabled={busy === job.event_key} className="text-emerald-800 underline disabled:opacity-50" onClick={() => retry(job.event_key)}>Retry</button>}</td>
      </tr>)}</tbody>
    </table>{jobs.length === 0 && <p className="text-sm text-slate-500 p-2">No queued notifications.</p>}</div>
  </section>;
}
