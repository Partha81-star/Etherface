import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";

type Props = {
  status: "verified" | "mismatch" | "not_registered";
};

export function StatusBadge({ status }: Props) {
  const styles = {
    verified: {
      icon: <CheckCircle2 aria-hidden="true" size={20} />,
      label: "Verified",
      className: "border-mint/30 bg-mint/10 text-mint",
    },
    mismatch: {
      icon: <AlertTriangle aria-hidden="true" size={20} />,
      label: "Mismatch",
      className: "border-red-400/30 bg-red-400/10 text-red-300",
    },
    not_registered: {
      icon: <CircleDashed aria-hidden="true" size={20} />,
      label: "Not registered",
      className: "border-white/15 bg-white/5 text-slate-300",
    },
  }[status];

  return (
    <div
      role="status"
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold uppercase tracking-[0.14em] ${styles.className}`}
    >
      {styles.icon}
      {styles.label}
    </div>
  );
}
