import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../AdminAuthContext';
import {
  Building2,
  Plus,
  Users,
  Calendar,
  Layers,
  Key,
  Edit2,
  X,
  Check,
  AlertCircle
} from 'lucide-react';

const AdminOrganisations = () => {
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
    allocated_sessions: '',
    contact_person: '',
    contact_email: '',
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

  // Organisation Users View
  const [orgUsers, setOrgUsers] = useState({});

  const fetchOrganisations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin-ops/organisations');
      setOrganisations(res.data || []);
      // fetch users for each org
      for (const org of res.data || []) {
        try {
          const uRes = await api.get(`/admin-ops/organisations/${org.id}/users`);
          setOrgUsers(prev => ({ ...prev, [org.id]: uRes.data || [] }));
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
      allocated_sessions: '',
      contact_person: '',
      contact_email: '',
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
      allocated_sessions: org.allocated_sessions != null ? org.allocated_sessions.toString() : '',
      contact_person: org.contact_person || '',
      contact_email: org.contact_email || '',
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
        allocated_sessions: orgForm.allocated_sessions ? parseInt(orgForm.allocated_sessions, 10) : null,
        contact_person: orgForm.contact_person.trim() || null,
        contact_email: orgForm.contact_email.trim() || null,
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

                  <div className="flex items-center gap-2">
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
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-[10px] text-slate-400 block font-semibold">Allocated Pool</span>
                    <span className="font-bold text-slate-900 text-sm">
                      {org.allocated_sessions != null ? `${org.allocated_sessions} sessions` : 'Unlimited / Not set'}
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

      {/* Organisation Modal */}
      {orgModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
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

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Contract Allocated Sessions Pool</label>
                <input
                  type="number"
                  value={orgForm.allocated_sessions}
                  onChange={(e) => setOrgForm({ ...orgForm, allocated_sessions: e.target.value })}
                  placeholder="e.g. 300"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                />
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
