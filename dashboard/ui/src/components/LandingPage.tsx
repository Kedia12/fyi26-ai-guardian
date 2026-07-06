import { useRef, useState } from 'react';
import HeroCarousel from './HeroCarousel';
import LandingNav, { LandingView } from './LandingNav';
import AboutSection from './AboutSection';
import FeatureSection from './FeatureSection';
import Login from './Login';

export default function LandingPage() {
  const [activeView, setActiveView] = useState<LandingView>('about');
  const [showLogin, setShowLogin] = useState(false);
  const aboutRef = useRef<HTMLDivElement>(null);
  const featureRef = useRef<HTMLDivElement>(null);

  if (showLogin) {
    return <Login onBack={() => setShowLogin(false)} />;
  }

  function selectView(view: LandingView) {
    setActiveView(view);
    const target = view === 'about' ? aboutRef.current : featureRef.current;
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className="min-h-screen bg-guardian-bg text-guardian-text font-sans">
      <div className="relative overflow-hidden min-h-screen flex flex-col">
        <HeroCarousel />
        <LandingNav
          activeView={activeView}
          onSelectView={selectView}
          onSignIn={() => setShowLogin(true)}
        />

        <div className="relative z-10 flex-1 flex items-center justify-center px-5 sm:px-8 py-12">
          <div className="max-w-3xl text-center">
            <span className="text-guardian-accent text-xs font-semibold uppercase tracking-widest">
              Autonomous Drone Safety
            </span>
            <h1 className="text-guardian-text font-bold text-4xl sm:text-5xl leading-tight mt-3 mb-5">
              What the future holds for flight safety
            </h1>
            <p className="text-guardian-muted text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
              Real-time telemetry, rule-based alerts, and ML anomaly detection for drone
              operations — so problems get caught in the air, not after the flight.
            </p>
          </div>
        </div>
      </div>

      <div ref={aboutRef} className="pt-16 sm:pt-24 scroll-mt-20">
        <AboutSection />
      </div>
      <div ref={featureRef} className="scroll-mt-20">
        <FeatureSection />
      </div>

      <p className="text-center text-guardian-dim text-[11px] pb-10 tracking-wide">
        Secured access &middot; FYI26 Guardian Systems
      </p>
    </div>
  );
}
