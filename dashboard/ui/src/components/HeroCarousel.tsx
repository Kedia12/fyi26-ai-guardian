import { useEffect, useRef, useState } from 'react';

const PANELS = [
  'radial-gradient(circle at 20% 20%, rgba(99,179,237,0.35), transparent 55%), radial-gradient(circle at 80% 80%, rgba(43,108,176,0.35), transparent 55%), linear-gradient(135deg, #0f1117 0%, #1a2942 100%)',
  'radial-gradient(circle at 75% 25%, rgba(99,179,237,0.30), transparent 50%), radial-gradient(circle at 25% 75%, rgba(99,179,237,0.20), transparent 50%), linear-gradient(160deg, #0f1117 0%, #16233d 100%)',
  'radial-gradient(circle at 50% 50%, rgba(99,179,237,0.25), transparent 60%), linear-gradient(200deg, #0f1117 0%, #1c2b4a 100%)',
];

export default function HeroCarousel() {
  const [index, setIndex] = useState(0);
  const reducedMotion = useRef(
    typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  useEffect(() => {
    if (reducedMotion.current) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % PANELS.length), 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden">
      {PANELS.map((bg, i) => (
        <div
          key={i}
          className="absolute inset-0 transition-opacity duration-1000 ease-in-out"
          style={{ background: bg, opacity: i === index ? 1 : 0 }}
        />
      ))}

      <div
        className="absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)',
          backgroundSize: '56px 56px',
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-guardian-bg/40 to-guardian-bg" />
    </div>
  );
}
