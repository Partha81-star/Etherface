import { ArrowUpRight, Blocks, CircleCheck, LoaderCircle, RefreshCw } from "lucide-react";
import type { ChainRegistration, VerificationStatus } from "../api/client";
import { StatusBadge } from "./StatusBadge";

type Props = {
  registration: ChainRegistration | null;
  status: VerificationStatus | null;
  registering: boolean;
  verifying: boolean;
  error: string | null;
  onRegister: () => void;
  onVerify: () => void;
};

function HashField({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg border border-line bg-black/20 p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="break-all font-mono text-sm leading-6 text-slate-200">{value || "—"}</p>
    </div>
  );
}

export function ChainVerifyStep({ registration, status, registering, verifying, error, onRegister, onVerify }: Props) {
  if (!registration) {
    return (
      <section className="panel p-5 sm:p-7" aria-labelledby="chain-heading">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div><p className="eyebrow">Immutable anchor</p><h2 id="chain-heading">Register on blockchain</h2></div>
          <Blocks className="text-amber" size={28} />
        </div>
        <p className="max-w-xl leading-7 text-muted">Create a tamper-evident fingerprint from the matched image and its canonical post metadata. No face encoding or image bytes are written on-chain.</p>
        <div className="mt-7 rounded-lg border border-amber/20 bg-amber/[0.06] p-4 text-sm leading-6 text-amber/90">Registration is immutable. Changing the local image or metadata afterward will produce a mismatch.</div>
        <button className="button-primary mt-7 w-full justify-center sm:w-auto" disabled={registering} onClick={onRegister}>
          {registering ? <LoaderCircle className="animate-spin" size={18} /> : <Blocks size={18} />}
          {registering ? "Waiting for confirmation…" : "Register on blockchain"}
        </button>
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="chain-heading">
      <div className="panel-heading">
        <div><p className="eyebrow text-mint">Transaction confirmed</p><h2 id="chain-heading">On-chain anchor</h2></div>
        <CircleCheck className="text-mint" size={28} />
      </div>
      <div className="grid gap-3 p-5 sm:p-6">
        <HashField label="Content hash" value={registration.content_hash} />
        <div className="grid gap-3 sm:grid-cols-2">
          <HashField label="Transaction" value={registration.tx_hash} />
          <HashField label="Contract" value={registration.contract_address} />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4 pt-3">
          <p className="font-mono text-sm text-muted">block #{registration.block_number.toLocaleString()}</p>
          {registration.explorer_url && <a className="inline-flex items-center gap-2 text-sm font-semibold text-cyan" href={registration.explorer_url} target="_blank" rel="noreferrer">View explorer <ArrowUpRight size={15} /></a>}
        </div>
      </div>
      <div className="border-t border-line p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div><p className="eyebrow">Integrity check</p><h3 className="text-lg font-semibold text-white">Compare both records</h3></div>
          {status && <StatusBadge status={status.status} />}
        </div>
        <button className="button-secondary" disabled={verifying} onClick={onVerify}>
          <RefreshCw className={verifying ? "animate-spin" : ""} size={17} />
          {verifying ? "Reading chain…" : "Verify integrity"}
        </button>
        {status && (
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            <HashField label="Local recomputation" value={status.local_hash} />
            <HashField label="On-chain record" value={status.on_chain_hash} />
          </div>
        )}
        {error && <p className="error-message" role="alert">{error}</p>}
      </div>
    </section>
  );
}
