export default function AboutSection() {
  return (
    <section className="max-w-3xl mx-auto px-5 sm:px-8 py-16 text-center">
      <span className="text-guardian-accent text-xs font-semibold uppercase tracking-widest">
        About
      </span>
      <h2 className="text-guardian-text text-3xl sm:text-4xl font-bold mt-3 mb-5">
        Autonomous Flight Monitoring &amp; Threat Detection
      </h2>
      <p className="text-guardian-muted text-sm sm:text-base leading-relaxed">
        AI Guardian watches live MAVLink telemetry from your drones and flags problems the
        moment they happen. It combines a rule-based safety layer — tuned for real failure
        modes like packet loss, GPS jumps, and battery drops — with a machine-learning
        anomaly detector trained on your own flight data, so operators get an early warning
        instead of reading about it in a post-flight log.
      </p>
      <p className="text-guardian-muted text-sm sm:text-base leading-relaxed mt-4">
        Every alert is backed by the raw telemetry that triggered it, a live aircraft map for
        situational awareness, and role-based access so admins can act on alerts while
        viewers get the same real-time picture without the controls.
      </p>
    </section>
  );
}
