import React, { useEffect, useState } from 'react';
import { api, useAdminAuth } from '../AdminAuthContext';
import { catInputToIso } from '../../utils/clinicalTime';
import { formatSessionDateTime } from '../AdminConstants';

const emptyForm = { date: '', fullDay: true, start: '09:00', end: '10:00', reason: '' };

export default function TherapistAvailability() {
  const { user } = useAdminAuth();
  const [form, setForm] = useState(emptyForm);
  const [blocks, setBlocks] = useState([]);
  const [therapists, setTherapists] = useState([]);
  const [selected, setSelected] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const isTherapist = user?.role === 'therapist';

  const reload = async () => {
    try {
      const [t, b] = await Promise.all([api.get('/therapists'), api.get('/therapists/blocks')]);
      setTherapists(t.data || []);
      setBlocks(b.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to load calendar blocks');
    }
  };
  useEffect(() => { reload(); }, []);

  const save = async (event) => {
    event.preventDefault();
    setMessage('');
    const id = isTherapist ? user?.therapist_id : selected;
    if (!id) { setMessage('No therapist profile is linked to your account. Ask the administrator to link one.'); return; }
    const start = form.date + 'T' + (form.fullDay ? '00:00' : form.start);
    const endDate = form.fullDay ? new Date(form.date + 'T12:00:00Z') : null;
    if (endDate) endDate.setUTCDate(endDate.getUTCDate() + 1);
    const end = form.fullDay
      ? endDate.toISOString().slice(0, 10) + 'T00:00'
      : form.date + 'T' + form.end;
    if (end <= start) { setMessage('End time must be after start time.'); return; }
    setBusy(true);
    try {
      await api.post('/therapists/blocks', {
        therapist_id: id,
        type: form.fullDay ? 'leave' : 'blocked_slot',
        starts_at: catInputToIso(start),
        ends_at: catInputToIso(end),
        reason: form.reason
      });
      setForm(emptyForm);
      setMessage('Unavailable time saved. Clients will no longer see these slots.');
      await reload();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to save blocked interval');
    } finally { setBusy(false); }
  };
  const remove = async (id) => {
    if (!window.confirm('Make this time available for booking again?')) return;
    try {
      await api.delete('/therapists/blocks/' + encodeURIComponent(id));
      await reload();
    } catch (error) { setMessage(error.response?.data?.detail || 'Unable to remove block'); }
  };
  const visible = isTherapist ? blocks : (selected ? blocks.filter(b => b.therapist_id === selected) : blocks);
  return <div className="max-w-5xl mx-auto space-y-6 p-2">
    <div className="bg-white border border-slate-200 rounded-2xl p-6">
      <h1 className="text-2xl font-bold text-slate-900">My Availability</h1>
      <p className="text-sm text-slate-600 mt-1">Block full days or selected hours. Times are in Botswana CAT (UTC+2). Existing appointments are protected.</p>
      {message && <p role="status" className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{message}</p>}
      <form onSubmit={save} className="mt-5 grid gap-4 md:grid-cols-2">
        {!isTherapist && <label className="text-sm font-semibold">Therapist<select required value={selected} onChange={e => setSelected(e.target.value)} className="block mt-1 w-full border rounded-lg p-2"><option value="">Select therapist</option>{therapists.map(t => <option value={t.id} key={t.id}>{t.name}</option>)}</select></label>}
        <label className="text-sm font-semibold">Date<input required type="date" value={form.date} onChange={e => setForm({...form, date:e.target.value})} className="block mt-1 w-full border rounded-lg p-2" /></label>
        <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={form.fullDay} onChange={e => setForm({...form, fullDay:e.target.checked})} /> Block entire day</label>
        {!form.fullDay && <>
          <label className="text-sm font-semibold">From (CAT)<input type="time" value={form.start} onChange={e => setForm({...form, start:e.target.value})} required className="block mt-1 w-full border rounded-lg p-2" /></label>
          <label className="text-sm font-semibold">Until (CAT)<input type="time" value={form.end} onChange={e => setForm({...form, end:e.target.value})} required className="block mt-1 w-full border rounded-lg p-2" /></label>
        </>}
        <label className="text-sm font-semibold md:col-span-2">Reason (optional)<input value={form.reason} onChange={e => setForm({...form, reason:e.target.value})} maxLength={250} placeholder="Leave, training, personal appointment..." className="block mt-1 w-full border rounded-lg p-2" /></label>
        <button disabled={busy} type="submit" className="md:col-span-2 rounded-lg bg-emerald-700 p-3 text-white font-semibold disabled:opacity-50">{busy ? 'Saving...' : 'Block selected time'}</button>
      </form>
    </div>
    <div className="bg-white border border-slate-200 rounded-2xl p-6">
      <h2 className="text-lg font-bold mb-3">Blocked time</h2>
      {visible.length === 0 ? <p className="text-sm text-slate-500">No blocked dates or times.</p> : <div className="space-y-3">{visible.map(b => <div key={b.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border rounded-xl p-3 text-sm">
        <div><div className="font-semibold">{formatSessionDateTime(b.starts_at).full} – {formatSessionDateTime(b.ends_at).full} CAT</div><div className="text-slate-500">{b.reason || b.type.replace(/_/g,' ')}</div></div>
        <button onClick={() => remove(b.id)} className="rounded-lg border border-rose-200 px-3 py-2 text-rose-700">Remove block</button>
      </div>)}</div>}
    </div>
  </div>;
}
