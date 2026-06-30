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
    function tick() {
      void savedCallback.current();
    }
    if (immediate) tick();
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, immediate]);
}
