import { useState, useEffect } from 'react';

interface HeaderProps {
  activeCount: number;
}

export default function Header({ activeCount }: HeaderProps) {
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="bg-guardian-card border-b border-guardian-border px-6 py-3 flex items-center gap-4 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <span className="text-guardian-accent text-xl">▷</span>
        <h1 className="text-guardian-accent font-semibold text-lg tracking-wide">
          AI Guardian
        </h1>
        <span className="bg-blue-800/60 text-blue-200 text-[10px] px-2.5 py-0.5 rounded-full font-bold tracking-widest uppercase border border-blue-700/50">
          FYI26
        </span>
      </div>

      <div className="flex items-center gap-2 ml-2">
        {activeCount > 0 ? (
          <div className="flex items-center gap-1.5 bg-red-950/60 border border-red-800/60 text-red-400 text-xs font-semibold px-3 py-1 rounded-full">
            <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse" />
            {activeCount} ACTIVE ALERT{activeCount > 1 ? 'S' : ''}
          </div>
        ) : (
          <div className="flex items-center gap-1.5 bg-green-950/40 border border-green-800/40 text-green-500 text-xs font-semibold px-3 py-1 rounded-full">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
            ALL CLEAR
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-4">
        <span className="text-guardian-muted text-xs font-mono tracking-wider">
          {time}
        </span>
      </div>
    </header>
  );
}
