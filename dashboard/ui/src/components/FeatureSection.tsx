import { ReactNode } from 'react';

interface Feature {
  title: string;
  description: string;
  icon: ReactNode;
}

const iconProps = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

const FEATURES: Feature[] = [
  {
    title: 'Live Telemetry Dashboard',
    description: 'Battery, altitude, GPS, IMU, and ML anomaly score updating in real time.',
    icon: (
      <svg {...iconProps}>
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    title: 'Rule-Based Safety Alerts',
    description:
      'Packet loss, out-of-order/duplicate packets, IMU dropout or freeze, low battery, GPS fix loss, GPS jumps, geofence breaches, and GPS/IMU inconsistency — checked on every packet.',
    icon: (
      <svg {...iconProps}>
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  },
  {
    title: 'ML Anomaly Scoring',
    description: 'An Isolation Forest model scores every packet against learned-normal flight behavior.',
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 5V2m0 20v-3m7-7h3M2 12h3m12.36-6.36l1.42-1.42M4.22 19.78l1.42-1.42m0-12.72L4.22 4.22m14.14 14.14l1.42 1.42" />
      </svg>
    ),
  },
  {
    title: 'Predictive Alerts',
    description: 'Forecasting flags degrading trends before they cross a hard threshold.',
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    title: 'Live Aircraft Map',
    description: 'Flight trails for monitored drones plus a live ADS-B traffic overlay.',
    icon: (
      <svg {...iconProps}>
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    ),
  },
  {
    title: 'AI Post-Flight Reports',
    description: "Claude summarizes a session's alerts into a readable after-action report.",
    icon: (
      <svg {...iconProps}>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
  {
    title: 'Role-Based Access',
    description: 'Admins get full control; viewers get a read-only feed of the same data.',
    icon: (
      <svg {...iconProps}>
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
];

export default function FeatureSection() {
  return (
    <section className="max-w-5xl mx-auto px-5 sm:px-8 py-16">
      <div className="text-center mb-10">
        <span className="text-guardian-accent text-xs font-semibold uppercase tracking-widest">
          Feature
        </span>
        <h2 className="text-guardian-text text-3xl sm:text-4xl font-bold mt-3">
          Everything you need to keep eyes on the fleet
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="bg-guardian-card border border-guardian-border rounded-xl p-5"
          >
            <div className="w-9 h-9 rounded-lg bg-guardian-accent/15 text-guardian-accent flex items-center justify-center mb-3">
              {f.icon}
            </div>
            <h3 className="text-guardian-text text-sm font-semibold mb-1.5">{f.title}</h3>
            <p className="text-guardian-muted text-xs leading-relaxed">{f.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
