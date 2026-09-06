import { ExternalLink, Fingerprint } from "lucide-react";
import { resolveApiUrl, type ScanResult } from "../api/client";

export function MatchResult({ result }: { result: ScanResult }) {
  const confidence = Math.max(0, Math.min(100, (1 - result.distance) * 100));
  return (
    <section aria-labelledby="match-heading" className="panel animate-in">
      <div className="panel-heading">
        <div>
          <p className="eyebrow text-mint">Authorized match</p>
          <h2 id="match-heading">Post identified</h2>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold text-mint">{result.distance.toFixed(4)}</p>
          <p className="text-xs uppercase tracking-wider text-muted">distance</p>
        </div>
      </div>
      <div className="grid gap-0 sm:grid-cols-[12rem_1fr]">
        <img
          className="h-56 w-full object-cover sm:h-full"
          src={resolveApiUrl(result.match.image_url)}
          alt={`Authorized post by ${result.match.author}`}
        />
        <div className="p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-mint/10 text-mint"><Fingerprint size={18} /></span>
            <div>
              <p className="font-semibold text-white">{result.match.author}</p>
              <p className="text-sm text-muted">{new Date(result.match.timestamp).toLocaleString()}</p>
            </div>
          </div>
          <p className="leading-7 text-slate-200">{result.match.caption}</p>
          <div className="mt-6">
            <div className="mb-2 flex justify-between text-xs uppercase tracking-wider text-muted">
              <span>Similarity signal</span><span>{confidence.toFixed(1)}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-cyan to-mint" style={{ width: `${confidence}%` }} /></div>
          </div>
          <a className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-cyan hover:text-white" href={result.match.source_url} target="_blank" rel="noreferrer">
            Open authorized source <ExternalLink size={14} />
          </a>
        </div>
      </div>
      <div className="border-t border-line px-5 py-3 font-mono text-xs text-muted">
        provider: {result.face_provider} · threshold: {result.tolerance.toFixed(2)}
      </div>
    </section>
  );
}
