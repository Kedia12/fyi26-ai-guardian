import { useState } from 'react';

export type LandingView = 'about' | 'feature';

interface LandingNavProps {
  activeView: LandingView;
  onSelectView: (view: LandingView) => void;
  onSignIn: () => void;
}

const TABS: LandingView[] = ['about', 'feature'];

export default function LandingNav({ activeView, onSelectView, onSignIn }: LandingNavProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  function selectView(view: LandingView) {
    onSelectView(view);
    setMobileOpen(false);
  }

  return (
    <nav className="fixed top-0 inset-x-0 z-30">
      <div className="absolute inset-x-0 top-0 h-36 bg-gradient-to-b from-guardian-bg/85 via-guardian-bg/45 to-transparent backdrop-blur-sm pointer-events-none" />

      <div className="relative px-5 sm:px-8 py-5 flex items-center gap-3">
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          aria-label="Scroll to top"
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <span className="text-guardian-accent text-xl">▷</span>
          <span className="text-guardian-text font-bold text-lg tracking-wide">AI Guardian</span>
          <span className="bg-blue-800/60 text-blue-200 text-[10px] px-2.5 py-0.5 rounded-full font-bold tracking-widest uppercase border border-blue-700/50">
            FYI26
          </span>
        </button>

        <div className="hidden md:flex items-center gap-1 absolute left-1/2 -translate-x-1/2">
          {TABS.map((v) => (
            <button
              key={v}
              onClick={() => selectView(v)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium capitalize transition-colors
                ${
                  activeView === v
                    ? 'text-guardian-accent'
                    : 'text-guardian-muted hover:text-guardian-text'
                }`}
            >
              {v}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={onSignIn}
            className="px-4 py-1.5 rounded-lg text-sm font-semibold bg-[#2b6cb0] hover:bg-[#2c5282] text-white transition-colors"
          >
            Sign In
          </button>
          <button
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle menu"
            className="md:hidden text-guardian-text"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {mobileOpen && (
          <div className="absolute top-full left-0 right-0 md:hidden bg-guardian-card/95 backdrop-blur border-b border-guardian-border px-5 py-3 flex flex-col gap-1">
            {TABS.map((v) => (
              <button
                key={v}
                onClick={() => selectView(v)}
                className={`text-left px-3 py-2 rounded-lg text-sm font-medium capitalize transition-colors
                  ${
                    activeView === v
                      ? 'bg-guardian-accent/15 text-guardian-accent'
                      : 'text-guardian-muted hover:text-guardian-text'
                  }`}
              >
                {v}
              </button>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
