import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const HRAuthContext = createContext(null);

export const hrApi = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL || ''}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

hrApi.interceptors.request.use((config) => {
  const selectedOrganisationId = window.localStorage.getItem('fca_hr_admin_organisation_id');
  const url = String(config.url || '');
  if (selectedOrganisationId && url.startsWith('/hr/') && url !== '/hr/me') {
    config.params = {
      ...(config.params || {}),
      organisation_id: selectedOrganisationId
    };
  }
  return config;
});

export const HRAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [organisations, setOrganisations] = useState([]);
  const [organisationId, setOrganisationId] = useState(null);

  const checkAuth = async () => {
    try {
      // First resolve the base authenticated identity. /hr/me requires an
      // organisation scope for admins/super-admins and should not be used as a
      // generic session probe.
      const base = await hrApi.get('/me');
      const role = base.data?.role;

      if (role === 'hr_admin' || role === 'hr_viewer') {
        const scoped = await hrApi.get('/hr/me');
        setUser(scoped.data);
        setOrganisationId(scoped.data?.organisation_id || null);
        setOrganisations([]);
        window.localStorage.removeItem('fca_hr_admin_organisation_id');
      } else if (role === 'super_admin') {
        const orgRes = await hrApi.get('/admin-ops/organisations');
        const orgs = orgRes.data || [];
        setOrganisations(orgs);

        const remembered = window.localStorage.getItem('fca_hr_admin_organisation_id');
        const selected = orgs.find((org) => org.id === remembered) || orgs[0] || null;
        setOrganisationId(selected?.id || null);
        if (selected?.id) {
          window.localStorage.setItem('fca_hr_admin_organisation_id', selected.id);
        } else {
          window.localStorage.removeItem('fca_hr_admin_organisation_id');
        }
        setUser({
          ...base.data,
          organisation_id: selected?.id || null,
          organisation_name: selected?.name || null
        });
      } else {
        setUser(null);
      }
    } catch (err) {
      setUser(null);
      setOrganisations([]);
      setOrganisationId(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (username, password) => {
    const res = await hrApi.post('/login', { username, password });
    if (res.data.role !== 'hr_admin' && res.data.role !== 'hr_viewer' && res.data.role !== 'super_admin') {
      await hrApi.post('/logout');
      throw new Error('This portal is restricted to authorised Corporate HR accounts.');
    }
    await checkAuth();
    return res.data;
  };

  const selectOrganisation = (nextId) => {
    if (user?.role !== 'super_admin') return;
    const selected = organisations.find((org) => org.id === nextId) || null;
    setOrganisationId(selected?.id || null);
    if (selected?.id) {
      window.localStorage.setItem('fca_hr_admin_organisation_id', selected.id);
    } else {
      window.localStorage.removeItem('fca_hr_admin_organisation_id');
    }
    setUser((current) => current ? {
      ...current,
      organisation_id: selected?.id || null,
      organisation_name: selected?.name || null
    } : current);
  };

  const scopedParams = (params = {}) => {
    if (user?.role === 'super_admin' && organisationId) {
      return { ...params, organisation_id: organisationId };
    }
    return params;
  };

  const logout = async () => {
    try {
      await hrApi.post('/logout');
    } catch (err) {
      console.warn('Logout request warning:', err);
    }
    setUser(null);
    setOrganisations([]);
    setOrganisationId(null);
    window.localStorage.removeItem('fca_hr_admin_organisation_id');
  };

  return (
    <HRAuthContext.Provider value={{
      user,
      loading,
      login,
      logout,
      checkAuth,
      organisations,
      organisationId,
      selectOrganisation,
      scopedParams
    }}>
      {children}
    </HRAuthContext.Provider>
  );
};

export const useHRAuth = () => {
  const context = useContext(HRAuthContext);
  if (!context) {
    throw new Error('useHRAuth must be used within an HRAuthProvider');
  }
  return context;
};
