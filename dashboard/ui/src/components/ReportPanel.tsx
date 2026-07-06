import { useState } from 'react';
import { createPortal } from 'react-dom';

type ReportState = 'idle' | 'loading' | 'done' | 'error';

interface Props {
  isAdmin: boolean;
}

export default function ReportPanel({ isAdmin }: Props) {
  const [state, setState] = useState<ReportState>('idle');
  const [report, setReport] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [modalOpen, setModalOpen] = useState(false);

  async function handleGenerate() {
    setState('loading');
    setErrorMsg('');
    try {
      const r = await fetch('/api/report', { method: 'POST' });
      const data = await r.json();
      if (!r.ok || data.error) {
        setErrorMsg(data.error || 'Unknown error');
        setState('error');
        return;
      }
      setReport(data.report);
      setState('done');
      setModalOpen(true);
    } catch (e) {
      setErrorMsg('Could not reach the server.');
      setState('error');
    }
  }

  return (
    <>
      <div className="bg-guardian-card border border-guardian-border rounded-lg px-4 py-3 flex items-center justify-between">
        <div>
          <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
            Post-Flight AI Report
          </span>
          <p className="text-guardian-muted text-[11px] mt-0.5">
            Summarise this session's alerts using Claude AI.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {state === 'error' && (
            <span className="text-red-400 text-[11px] max-w-[220px] text-right">{errorMsg}</span>
          )}
          {state === 'done' && (
            <button
              onClick={() => setModalOpen(true)}
              className="text-[11px] text-[#90cdf4] underline underline-offset-2"
            >
              View report
            </button>
          )}
          {isAdmin ? (
            <button
              onClick={handleGenerate}
              disabled={state === 'loading'}
              className="px-3 py-1.5 rounded text-xs font-semibold transition-colors
                bg-[#2b6cb0] hover:bg-[#2c5282] disabled:opacity-50 disabled:cursor-not-allowed
                text-white"
            >
              {state === 'loading' ? 'Generating…' : 'Generate Report'}
            </button>
          ) : (
            <span className="text-guardian-muted text-[11px] italic">Admin only</span>
          )}
        </div>
      </div>

      {modalOpen && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70"
          onClick={() => setModalOpen(false)}
        >
          <div
            className="bg-guardian-card border border-guardian-border rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between rounded-t-lg">
              <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
                Post-Flight AI Report
              </span>
              <button
                onClick={() => setModalOpen(false)}
                className="text-guardian-muted hover:text-guardian-text text-lg leading-none"
              >
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-5">
              <pre className="whitespace-pre-wrap font-mono text-[12px] text-guardian-text leading-relaxed">
                {report}
              </pre>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
