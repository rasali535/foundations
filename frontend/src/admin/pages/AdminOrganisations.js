import React, { useState, useEffect, useCallback } from 'react';
import { api, useAdminAuth } from '../AdminAuthContext';
import {
  Building2,
  Plus,
  Users,
  Key,
  Edit2,
  X,
  AlertCircle,
  Link2,
  Copy,
  ExternalLink,
  Upload,
  Receipt,
  Trash2
} from 'lucide-react';

const AdminOrganisations = () => {
  const { user } = useAdminAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const [organisations, setOrganisations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals state
  const [orgModalOpen, setOrgModalOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState(null);
  const [orgForm, setOrgForm] = useState({
    name: '',
    code: '',
    status: 'active',
    contract_start: '',
    contract_end: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    billing_contact_name: '',
    billing_email: '',
    billing_phone: '',
    billing_address: '',
    registration_number: '',
    tax_number: '',
    purchase_order_reference: '',
    billing_currency: 'BWP',
    payment_terms_days: '30',
    rate_individual: '',
    rate_couple: '',
    rate_family: '',
    invoice_notes: '',
    notes: ''
  });

  const [userModalOpen, setUserModalOpen] = useState(false);
  const [selectedOrgForUser, setSelectedOrgForUser] = useState(null);
  const [userForm, setUserForm] = useState({
    username: '',
    password: '',
    name: '',
    email: '',
    role: 'hr_admin'
  });

  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [copiedOrgId, setCopiedOrgId] = useState(null);

  const getIntakeLink = (org) => {
    const code = encodeURIComponent(String(org?.code || '').trim().toUpperCase());
    return `${window.location.origin}/intake/${code}`;
  };

  const handleCopyIntakeLink = async (org) => {
    const url = getIntakeLink(org);
    try {
      await navigator.clipboard.writeText(url);
      setCopiedOrgId(org.id);
      window.setTimeout(() => setCopiedOrgId(null), 1800);
    } catch (err) {
      setActionError(`Could not copy automatically. Intake link: ${url}`);
    }
  };

  // Organisation Users & Corporate Roster View
  const [orgUsers, setOrgUsers] = useState({});
  const [orgContacts, setOrgContacts] = useState({});
  const [orgPools, setOrgPools] = useState({});
  const [rosterModalOpen, setRosterModalOpen] = useState(false);
  const [selectedOrgForRoster, setSelectedOrgForRoster] = useState(null);
  const [bulkRosterText, setBulkRosterText] = useState('');
  const [rosterLoading, setRosterLoading] = useState(false);

  const fetchOrganisations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin-ops/organisations');
      setOrganisations(res.data || []);
      // Fetch portal users and corporate roster/pool for each organisation.
      for (const org of res.data || []) {
        try {
          const [uRes, cRes] = await Promise.all([
            api.get(`/admin-ops/organisations/${org.id}/users`),
            api.get(`/admin-ops/organisations/${org.id}/contacts`)
          ]);
          setOrgUsers(prev => ({ ...prev, [org.id]: uRes.data || [] }));
          setOrgContacts(prev => ({ ...prev, [org.id]: cRes.data?.contacts || [] }));
          setOrgPools(prev => ({ ...prev, [org.id]: cRes.data?.pool || null }));
        } catch (e) {}
      }
    } catch (err) {
      setError('Failed to load corporate organisations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrganisations();
  }, [fetchOrganisations]);

  const handleOpenCreateOrg = () => {
    setEditingOrg(null);
    setOrgForm({
      name: '',
      code: '',
      status: 'active',
      contract_start: '',
      contract_end: '',
      contact_person: '',
      contact_email: '',
      contact_phone: '',
      billing_contact_name: '',
      billing_email: '',
      billing_phone: '',
      billing_address: '',
      registration_number: '',
      tax_number: '',
      purchase_order_reference: '',
      billing_currency: 'BWP',
      payment_terms_days: '30',
      rate_individual: '',
      rate_couple: '',
      rate_family: '',
      invoice_notes: '',
      notes: ''
    });
    setActionError('');
    setOrgModalOpen(true);
  };

  const handleOpenEditOrg = (org) => {
    setEditingOrg(org);
    setOrgForm({
      name: org.name,
      code: org.code,
      status: org.status,
      contract_start: org.contract_start || '',
      contract_end: org.contract_end || '',
      contact_person: org.contact_person || '',
      contact_email: org.contact_email || '',
      contact_phone: org.contact_phone || '',
      billing_contact_name: org.billing_contact_name || '',
      billing_email: org.billing_email || '',
      billing_phone: org.billing_phone || '',
      billing_address: org.billing_address || '',
      registration_number: org.registration_number || '',
      tax_number: org.tax_number || '',
      purchase_order_reference: org.purchase_order_reference || '',
      billing_currency: org.billing_currency || 'BWP',
      payment_terms_days: String(org.payment_terms_days ?? 30),
      rate_individual: org.rate_individual != null ? String(org.rate_individual) : '',
      rate_couple: org.rate_couple != null ? String(org.rate_couple) : '',
      rate_family: org.rate_family != null ? String(org.rate_family) : '',
      invoice_notes: org.invoice_notes || '',
      notes: org.notes || ''
    });
    setActionError('');
    setOrgModalOpen(true);
  };

  const handleSaveOrg = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      const payload = {
        name: orgForm.name.trim(),
        code: orgForm.code.trim().toUpperCase(),
        status: orgForm.status,
        contract_start: orgForm.contract_start || null,
        contract_end: orgForm.contract_end || null,
        contact_person: orgForm.contact_person.trim() || null,
        contact_email: orgForm.contact_email.trim() || null,
        contact_phone: orgForm.contact_phone.trim() || null,
        billing_contact_name: orgForm.billing_contact_name.trim() || null,
        billing_email: orgForm.billing_email.trim() || null,
        billing_phone: orgForm.billing_phone.trim() || null,
        billing_address: orgForm.billing_address.trim() || null,
        registration_number: orgForm.registration_number.trim() || null,
        tax_number: orgForm.tax_number.trim() || null,
        purchase_order_reference: orgForm.purchase_order_reference.trim() || null,
        billing_currency: (orgForm.billing_currency || 'BWP').trim().toUpperCase(),
        payment_terms_days: parseInt(orgForm.payment_terms_days || '30', 10),
        rate_individual: orgForm.rate_individual ? parseFloat(orgForm.rate_individual) : null,
        rate_couple: orgForm.rate_couple ? parseFloat(orgForm.rate_couple) : null,
        rate_family: orgForm.rate_family ? parseFloat(orgForm.rate_family) : null,
        invoice_notes: orgForm.invoice_notes.trim() || null,
        notes: orgForm.notes.trim() || null
      };

      if (editingOrg) {
        await api.put(`/admin-ops/organisations/${editingOrg.id}`, payload);
      } else {
        await api.post('/admin-ops/organisations', payload);
      }
      setOrgModalOpen(false);
      fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to save organisation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenCreateUser = (org) => {
    setSelectedOrgForUser(org);
    setUserForm({
      username: '',
      password: '',
      name: '',
      email: '',
      role: 'hr_admin'
    });
    setActionError('');
    setUserModalOpen(true);
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      await api.post(`/admin-ops/organisations/${selectedOrgForUser.id}/users`, {
        username: userForm.username.trim().toLowerCase(),
        password: userForm.password,
        name: userForm.name.trim(),
        email: userForm.email.trim().toLowerCase(),
        role: userForm.role
      });
      setUserModalOpen(false);
      fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to create HR portal account.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenRoster = (org) => {
    setSelectedOrgForRoster(org);
    setBulkRosterText('');
    setActionError('');
    setRosterModalOpen(true);
  };

  const handleDeleteOrganisation = async (org) => {
    if (!isSuperAdmin) return;
    const confirmation = window.prompt(
      `This permanently deletes ${org.name} and linked operational records. Type ${org.code} to confirm.`
    );
    if (confirmation !== org.code) return;

    setActionLoading(true);
    setActionError('');
    try {
      await api.delete(`/admin-ops/organisations/${org.id}`, { params: { cascade: true } });
      await fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Could not delete organisation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteOrgUser = async (org, account) => {
    if (!isSuperAdmin) return;
    if (!window.confirm(`Delete HR portal user ${account.name} (${account.user_id})?`)) return;
    setActionLoading(true);
    setActionError('');
    try {
      await api.delete(`/admin-ops/organisations/${org.id}/users/${account.id}`);
      await fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Could not delete HR portal user.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteRosterContact = async (contact) => {
    if (!isSuperAdmin || !selectedOrgForRoster) return;
    if (!window.confirm(`Delete ${contact.name || contact.email} from this organisation roster?`)) return;
    setActionLoading(true);
    setActionError('');
    try {
      const res = await api.delete(
        `/admin-ops/organisations/${selectedOrgForRoster.id}/contacts/${contact.id}`
      );
      setOrgContacts(prev => ({
        ...prev,
        [selectedOrgForRoster.id]: (prev[selectedOrgForRoster.id] || []).filter(item => item.id !== contact.id)
      }));
      if (res.data?.pool) {
        setOrgPools(prev => ({ ...prev, [selectedOrgForRoster.id]: res.data.pool }));
      }
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Could not delete roster member.');
    } finally {
      setActionLoading(false);
    }
  };

  const parseRosterText = (text) => {
    return text
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)
      .map(line => {
        const delimiter = line.includes('\t') ? '\t' : ',';
        const parts = line.split(delimiter).map(value => value.trim());
        if (parts.length === 1 && parts[0].includes('@')) {
          return { name: '', email: parts[0], phone: '', department: '', job_title: '', contact_type: 'employee' };
        }
        return {
          name: parts[0] || '',
          email: parts[1] || '',
          phone: parts[2] || '',
          department: parts[3] || '',
          job_title: parts[4] || '',
          contact_type: parts[5] || 'employee'
        };
      })
      .filter(row => row.email && row.email.includes('@'));
  };

  const handleRosterStatus = async (contact) => {
    if (!selectedOrgForRoster) return;
    try {
      const nextActive = contact.active === false;
      const res = await api.patch(
        `/admin-ops/organisations/${selectedOrgForRoster.id}/contacts/${contact.id}/status`,
        null,
        { params: { active: nextActive } }
      );
      setOrgContacts(prev => ({
        ...prev,
        [selectedOrgForRoster.id]: (prev[selectedOrgForRoster.id] || []).map(item =>
          item.id === contact.id ? { ...item, active: nextActive } : item
        )
      }));
      if (res.data?.pool) {
        setOrgPools(prev => ({ ...prev, [selectedOrgForRoster.id]: res.data.pool }));
      }
      await fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Could not update roster member status.');
    }
  };

  const handleBulkRosterSave = async () => {
    if (!selectedOrgForRoster) return;
    const contacts = parseRosterText(bulkRosterText);
    if (!contacts.length) {
      setActionError('Add at least one valid email. Use: Name, Email, Phone, Department, Job Title.');
      return;
    }
    setRosterLoading(true);
    setActionError('');
    try {
      const res = await api.post(
        `/admin-ops/organisations/${selectedOrgForRoster.id}/contacts/bulk`,
        { contacts }
      );
      setOrgContacts(prev => ({ ...prev, [selectedOrgForRoster.id]: res.data?.contacts || [] }));
      setOrgPools(prev => ({ ...prev, [selectedOrgForRoster.id]: res.data?.pool || null }));
      setBulkRosterText('');
      await fetchOrganisations();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to import corporate contacts.');
    } finally {
      setRosterLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900">
            Corporate Client Organisations
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage enterprise contracts, allocated session pools, and HR portal accounts
          </p>
        </div>
        <button
          onClick={handleOpenCreateOrg}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow transition self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Corporate Organisation</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Organisations List */}
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-2">
          <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-500">Loading corporate partners...</p>
        </div>
      ) : organisations.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
          No corporate organisations registered yet. Click &quot;Add Corporate Organisation&quot; to configure one.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {organisations.map((org) => {
            const usersList = orgUsers[org.id] || [];
            const contactsList = orgContacts[org.id] || [];
            const pool = orgPools[org.id] || {
              member_count: contactsList.filter(c => c.active !== false && c.email).length,
              allocated_sessions: org.allocated_sessions || 0,
              approved_extra_sessions: 0
            };
            return (
              <div key={org.id} className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm">
                      <Building2 className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-slate-900 text-base">{org.name}</h3>
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                          {org.code}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          org.status === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {org.status}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {org.contact_person ? `Lead: ${org.contact_person} (${org.contact_email || 'No email'})` : 'No contact specified'}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => handleOpenRoster(org)}
                      className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold rounded-lg border border-emerald-200 transition inline-flex items-center gap-1.5"
                    >
                      <Users className="w-3.5 h-3.5" />
                      <span>Employee Roster</span>
                    </button>
                    <button
                      onClick={() => handleOpenCreateUser(org)}
                      className="px-3 py-1.5 bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs font-bold rounded-lg border border-teal-200 transition inline-flex items-center gap-1.5"
                    >
                      <Key className="w-3.5 h-3.5" />
                      <span>+ HR Portal User</span>
                    </button>
                    <button
                      onClick={() => handleOpenEditOrg(org)}
                      className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition"
                      title="Edit Organisation"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    {isSuperAdmin && (
                      <button
                        type="button"
                        onClick={() => handleDeleteOrganisation(org)}
                        disabled={actionLoading}
                        className="p-1.5 text-rose-500 hover:text-rose-700 rounded-lg hover:bg-rose-50 transition disabled:opacity-50"
                        title="Delete Organisation"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-[10px] text-slate-400 block font-semibold">Allocated Pool</span>
                    <span className="font-bold text-slate-900 text-sm">
                      {pool.allocated_sessions} sessions
                    </span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      {pool.member_count} people × 4
                      {pool.approved_extra_sessions > 0 ? ` + ${pool.approved_extra_sessions} therapist-approved` : ''}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-[10px] text-slate-400 block font-semibold">Contract Start</span>
                    <span className="font-semibold text-slate-800">{org.contract_start || 'N/A'}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-[10px] text-slate-400 block font-semibold">Contract End</span>
                    <span className="font-semibold text-slate-800">{org.contract_end || 'N/A'}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-[10px] text-slate-400 block font-semibold">HR Portal Accounts</span>
                    <span className="font-bold text-teal-700 text-sm">{usersList.length} Active</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-teal-100 bg-teal-50/60">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-teal-900 font-bold text-xs">
                        <Link2 className="w-4 h-4" />
                        Corporate / EAP Intake Link
                      </div>
                      <p className="mt-1 text-[11px] text-teal-700 break-all">
                        {getIntakeLink(org)}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500">
                        Clients using this link are automatically attributed to {org.name}; they do not select their employer manually.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleCopyIntakeLink(org)}
                        className="px-3 py-2 bg-white hover:bg-teal-100 text-teal-800 text-xs font-bold rounded-lg border border-teal-200 transition inline-flex items-center gap-1.5"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        {copiedOrgId === org.id ? 'Copied' : 'Copy Link'}
                      </button>
                      <a
                        href={getIntakeLink(org)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold rounded-lg transition inline-flex items-center gap-1.5"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Open
                      </a>
                    </div>
                  </div>
                </div>

                {usersList.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 text-xs">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
                      Authorised Corporate HR Users:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {usersList.map((u) => (
                        <div key={u.id} className="px-3 py-1 bg-slate-100 rounded-lg flex items-center gap-2 border border-slate-200">
                          <span className="font-bold text-slate-800">{u.name}</span>
                          <span className="text-slate-400">({u.user_id})</span>
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-teal-100 text-teal-800 uppercase">
                            {u.role}
                          </span>
                          {isSuperAdmin && (
                            <button
                              type="button"
                              onClick={() => handleDeleteOrgUser(org, u)}
                              className="ml-1 text-rose-500 hover:text-rose-700"
                              title="Delete HR portal user"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Corporate Employee Roster Modal */}
      {rosterModalOpen && selectedOrgForRoster && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl border border-slate-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Corporate Employee Roster</h3>
                <span className="text-[11px] text-emerald-700 font-semibold">{selectedOrgForRoster.name}</span>
              </div>
              <button onClick={() => setRosterModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-4 bg-slate-50 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Active People</span>
                  <p className="text-xl font-black text-slate-900">{orgPools[selectedOrgForRoster.id]?.member_count || 0}</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Base Allocation</span>
                  <p className="text-xl font-black text-slate-900">{(orgPools[selectedOrgForRoster.id]?.member_count || 0) * 4}</p>
                  <span className="text-[10px] text-slate-500">4 sessions per person</span>
                </div>
                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                  <span className="text-[10px] uppercase font-bold text-emerald-700">Total Pool</span>
                  <p className="text-xl font-black text-emerald-800">{orgPools[selectedOrgForRoster.id]?.allocated_sessions || 0}</p>
                  <span className="text-[10px] text-emerald-700">Includes approved extras</span>
                </div>
              </div>

              {actionError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{actionError}</div>
              )}

              <div className="p-4 border border-slate-200 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Upload className="w-4 h-4 text-emerald-700" />
                  <h4 className="text-sm font-bold text-slate-900">Bulk add / update people</h4>
                </div>
                <p className="text-[11px] text-slate-500 mb-3">
                  Paste from Excel or CSV. One person per line: <b>Name, Email, Phone, Department, Job Title</b>. Email is required and acts as the unique roster key.
                </p>
                <textarea
                  rows="7"
                  value={bulkRosterText}
                  onChange={(e) => setBulkRosterText(e.target.value)}
                  placeholder={"Jane Doe, jane@company.com, +267..., Finance, Manager\nJohn Doe, john@company.com, +267..., Operations, Officer"}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono"
                />
                <div className="flex justify-end mt-3">
                  <button
                    type="button"
                    onClick={handleBulkRosterSave}
                    disabled={rosterLoading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg"
                  >
                    {rosterLoading ? 'Importing...' : 'Import / Update Roster'}
                  </button>
                </div>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-700">
                  Current Roster
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-slate-400 uppercase bg-white border-b border-slate-100">
                      <tr>
                        <th className="px-4 py-2">Person</th>
                        <th className="px-4 py-2">Email</th>
                        <th className="px-4 py-2">Phone</th>
                        <th className="px-4 py-2">Department / Role</th>
                        <th className="px-4 py-2 text-center">Allocation</th>
                        <th className="px-4 py-2 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(orgContacts[selectedOrgForRoster.id] || []).length === 0 ? (
                        <tr><td colSpan="6" className="px-4 py-8 text-center text-slate-400">No employees added yet.</td></tr>
                      ) : (
                        (orgContacts[selectedOrgForRoster.id] || []).map(contact => (
                          <tr key={contact.id} className={contact.active === false ? 'opacity-50' : ''}>
                            <td className="px-4 py-3 font-semibold text-slate-800">{contact.name || '—'}</td>
                            <td className="px-4 py-3 text-slate-600">{contact.email}</td>
                            <td className="px-4 py-3 text-slate-600">{contact.phone || '—'}</td>
                            <td className="px-4 py-3 text-slate-600">
                              {[contact.department, contact.job_title].filter(Boolean).join(' • ') || '—'}
                            </td>
                            <td className="px-4 py-3 text-center font-bold text-slate-800">
                              {(contact.base_session_allocation || 4) + (contact.extra_sessions_approved || 0)}
                              {contact.extra_sessions_approved > 0 && (
                                <span className="block text-[9px] text-emerald-700">+{contact.extra_sessions_approved} approved</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleRosterStatus(contact)}
                                  className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition ${contact.active === false
                                    ? 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-emerald-50 hover:text-emerald-700'
                                    : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-rose-50 hover:text-rose-700'}`}
                                >
                                  {contact.active === false ? 'Reactivate' : 'Active'}
                                </button>
                                {isSuperAdmin && (
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteRosterContact(contact)}
                                    className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                                    title="Delete roster member"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <p className="text-[11px] text-slate-500">
                Employee roster data is operational entitlement data. Corporate HR dashboards still receive aggregate utilisation only and do not expose individual counselling activity.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Organisation Modal */}
      {orgModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl border border-slate-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">
                {editingOrg ? 'Edit Corporate Organisation' : 'Add Corporate Organisation'}
              </h3>
              <button onClick={() => setOrgModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleSaveOrg} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Org Name *</label>
                  <input
                    type="text"
                    required
                    value={orgForm.name}
                    onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })}
                    placeholder="e.g. Letshego Financial"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Code (Unique) *</label>
                  <input
                    type="text"
                    required
                    value={orgForm.code}
                    onChange={(e) => setOrgForm({ ...orgForm, code: e.target.value })}
                    placeholder="e.g. LETS"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs uppercase"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contract Start Date</label>
                  <input
                    type="date"
                    value={orgForm.contract_start}
                    onChange={(e) => setOrgForm({ ...orgForm, contract_start: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contract End Date</label>
                  <input
                    type="date"
                    value={orgForm.contract_end}
                    onChange={(e) => setOrgForm({ ...orgForm, contract_end: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-xs text-emerald-900">
                <strong>Session allocation is automatic.</strong>
                <p className="mt-1 text-emerald-800">
                  Every active employee email in the corporate roster receives 4 sessions. Extra sessions only increase the pool after therapist or clinical-lead approval.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={orgForm.contact_person}
                    onChange={(e) => setOrgForm({ ...orgForm, contact_person: e.target.value })}
                    placeholder="HR Lead Name"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Email</label>
                  <input
                    type="email"
                    value={orgForm.contact_email}
                    onChange={(e) => setOrgForm({ ...orgForm, contact_email: e.target.value })}
                    placeholder="hr@company.com"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Main Contact Phone</label>
                <input
                  type="text"
                  value={orgForm.contact_phone}
                  onChange={(e) => setOrgForm({ ...orgForm, contact_phone: e.target.value })}
                  placeholder="+267 ..."
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2 mb-3">
                  <Receipt className="w-4 h-4 text-emerald-700" />
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Corporate Billing Profile</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input type="text" value={orgForm.billing_contact_name} onChange={(e) => setOrgForm({ ...orgForm, billing_contact_name: e.target.value })} placeholder="Billing contact name" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="email" value={orgForm.billing_email} onChange={(e) => setOrgForm({ ...orgForm, billing_email: e.target.value })} placeholder="Billing email" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="text" value={orgForm.billing_phone} onChange={(e) => setOrgForm({ ...orgForm, billing_phone: e.target.value })} placeholder="Billing phone" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="text" value={orgForm.purchase_order_reference} onChange={(e) => setOrgForm({ ...orgForm, purchase_order_reference: e.target.value })} placeholder="Default PO / reference" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="text" value={orgForm.registration_number} onChange={(e) => setOrgForm({ ...orgForm, registration_number: e.target.value })} placeholder="Registration number" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="text" value={orgForm.tax_number} onChange={(e) => setOrgForm({ ...orgForm, tax_number: e.target.value })} placeholder="Tax / VAT number" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <textarea value={orgForm.billing_address} onChange={(e) => setOrgForm({ ...orgForm, billing_address: e.target.value })} placeholder="Billing address" rows="2" className="sm:col-span-2 w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Contract Billing Rules</span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                  <input type="text" value={orgForm.billing_currency} onChange={(e) => setOrgForm({ ...orgForm, billing_currency: e.target.value })} placeholder="Currency" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs uppercase" />
                  <input type="number" min="0" value={orgForm.payment_terms_days} onChange={(e) => setOrgForm({ ...orgForm, payment_terms_days: e.target.value })} placeholder="Payment terms days" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="number" min="0" step="0.01" value={orgForm.rate_individual} onChange={(e) => setOrgForm({ ...orgForm, rate_individual: e.target.value })} placeholder="Individual rate" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="number" min="0" step="0.01" value={orgForm.rate_couple} onChange={(e) => setOrgForm({ ...orgForm, rate_couple: e.target.value })} placeholder="Couple rate" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <input type="number" min="0" step="0.01" value={orgForm.rate_family} onChange={(e) => setOrgForm({ ...orgForm, rate_family: e.target.value })} placeholder="Family rate" className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                  <textarea value={orgForm.invoice_notes} onChange={(e) => setOrgForm({ ...orgForm, invoice_notes: e.target.value })} placeholder="Default invoice note" rows="2" className="col-span-2 sm:col-span-3 w-full px-3 py-2 border border-slate-200 rounded-lg text-xs" />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setOrgModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Save Organisation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create HR User Modal */}
      {userModalOpen && selectedOrgForUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Add HR Portal User</h3>
                <span className="text-[11px] text-teal-700 font-semibold">{selectedOrgForUser.name}</span>
              </div>
              <button onClick={() => setUserModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            {actionError && (
              <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            <form onSubmit={handleSaveUser} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={userForm.name}
                  onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  placeholder="e.g. Tshepo Modise"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Corporate Email Address *</label>
                <input
                  type="email"
                  required
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  placeholder="tshepo@company.com"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Username *</label>
                  <input
                    type="text"
                    required
                    value={userForm.username}
                    onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                    placeholder="e.g. letshego_hr"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Role</label>
                  <select
                    value={userForm.role}
                    onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="hr_admin">HR Admin</option>
                    <option value="hr_viewer">HR Viewer</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Initial Password *</label>
                <input
                  type="password"
                  required
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setUserModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  {actionLoading ? 'Creating User...' : 'Create HR Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminOrganisations;
