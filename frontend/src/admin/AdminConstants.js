// Centralized UI mappings for Foundations Counselling CRM & Booking Platform

export const SESSION_TYPE_COLORS = {
  individual: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-800 border border-blue-300',
    dot: 'bg-blue-500',
    label: 'Individual'
  },
  couple: {
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
    badge: 'bg-purple-100 text-purple-800 border border-purple-300',
    dot: 'bg-purple-500',
    label: 'Couple'
  },
  family: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    badge: 'bg-emerald-100 text-emerald-800 border border-emerald-300',
    dot: 'bg-emerald-500',
    label: 'Family'
  }
};

export const SESSION_MODE_CONFIG = {
  in_person: {
    label: 'In-Person',
    badge: 'bg-amber-100 text-amber-800 border border-amber-300',
    icon: 'Building2',
    description: 'FCA Central Clinic'
  },
  virtual: {
    label: 'Virtual',
    badge: 'bg-cyan-100 text-cyan-800 border border-cyan-300',
    icon: 'Video',
    description: 'Online Video Session'
  }
};

export const STATUS_CONFIG = {
  confirmed: { label: 'Confirmed', badge: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  pending: { label: 'Pending', badge: 'bg-amber-100 text-amber-800 border-amber-300' },
  completed: { label: 'Completed', badge: 'bg-blue-100 text-blue-800 border-blue-300' },
  cancelled: { label: 'Cancelled', badge: 'bg-rose-100 text-rose-800 border-rose-300' },
  late_cancelled_billable: { label: 'Late Cancel (Billed)', badge: 'bg-orange-100 text-orange-800 border-orange-300' },
  rescheduled: { label: 'Rescheduled', badge: 'bg-purple-100 text-purple-800 border-purple-300' },
  no_show: { label: 'No Show', badge: 'bg-slate-100 text-slate-700 border-slate-300' }
};

export const formatSessionDateTime = (isoString) => {
  if (!isoString) return 'N/A';
  try {
    const d = new Date(isoString);
    return {
      date: d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
      time: d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
      full: d.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    };
  } catch (e) {
    return { date: isoString, time: '', full: isoString };
  }
};
