import { useEffect, useRef } from 'react';

const useAutoRefresh = (callback, intervalMs, enabled = true) => {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || typeof callbackRef.current !== 'function' || !intervalMs) return undefined;

    const run = () => {
      if (document.visibilityState === 'visible') {
        callbackRef.current();
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
  }, [intervalMs, enabled]);
};

export default useAutoRefresh;
