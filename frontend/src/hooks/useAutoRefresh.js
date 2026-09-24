import { useEffect } from 'react';

const useAutoRefresh = (callback, intervalMs, enabled = true) => {
  useEffect(() => {
    if (!enabled || typeof callback !== 'function' || !intervalMs) return undefined;

    const run = () => {
      if (document.visibilityState === 'visible') {
        callback();
      }
    };

    const intervalId = window.setInterval(run, intervalMs);
    window.addEventListener('focus', run);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') run();
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', run);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [callback, intervalMs, enabled]);
};

export default useAutoRefresh;
