import React, { useEffect, useState } from 'react';
import { Download, MonitorDown } from 'lucide-react';

const isStandalone = () =>
  window.matchMedia?.('(display-mode: standalone)').matches ||
  window.navigator.standalone === true;

const InstallPortalButton = ({ label = 'Install App', compact = false }) => {
  const [installPrompt, setInstallPrompt] = useState(null);
  const [installed, setInstalled] = useState(isStandalone());

  useEffect(() => {
    const onBeforeInstall = (event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };

    const onInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
    };

    const displayMode = window.matchMedia?.('(display-mode: standalone)');
    const onDisplayModeChange = () => setInstalled(isStandalone());

    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    window.addEventListener('appinstalled', onInstalled);
    displayMode?.addEventListener?.('change', onDisplayModeChange);

    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall);
      window.removeEventListener('appinstalled', onInstalled);
      displayMode?.removeEventListener?.('change', onDisplayModeChange);
    };
  }, []);

  if (installed || !installPrompt) return null;

  const handleInstall = async () => {
    const prompt = installPrompt;
    if (!prompt) return;

    setInstallPrompt(null);
    await prompt.prompt();
    const choice = await prompt.userChoice;

    if (choice?.outcome !== 'accepted') {
      // The browser may emit a fresh beforeinstallprompt event later.
      setInstalled(isStandalone());
    }
  };

  if (compact) {
    return (
      <button
        type="button"
        onClick={handleInstall}
        className="inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
        title={label}
      >
        <Download className="w-3.5 h-3.5" />
        <span>{label}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleInstall}
      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition"
    >
      <MonitorDown className="w-4 h-4 text-emerald-600" />
      <span>{label}</span>
    </button>
  );
};

export default InstallPortalButton;
