import { useEffect, useRef } from 'react';

export function usePolling(
  callback: () => void | Promise<void>,
  intervalMs: number,
  immediate = true,
) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    let isRunning = false;
    async function tick() {
      if (isRunning) return;
      isRunning = true;
      try {
        await savedCallback.current();
      } finally {
        isRunning = false;
      }
    }
    if (immediate) void tick();
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, immediate]);
}
