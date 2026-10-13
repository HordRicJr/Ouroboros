import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone: string;
}) {
  return (
    <div className="stat-card fade-in" style={{ ["--tone" as string]: tone }}>
      <div className="stat-icon">
        <Icon size={19} strokeWidth={2} />
      </div>
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value" style={{ marginTop: 6 }}>
          {value}
        </div>
        {sub && <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  );
}

export function Panel({
  icon: Icon,
  title,
  badge,
  children,
  flush,
}: {
  icon: LucideIcon;
  title: string;
  badge?: ReactNode;
  children: ReactNode;
  flush?: boolean;
}) {
  return (
    <section className="panel fade-in">
      <div className="panel-head">
        <h2 className="panel-title">
          <Icon size={18} />
          {title}
        </h2>
        {badge !== undefined && <span className="badge">{badge}</span>}
      </div>
      {flush ? children : <div className="panel-body">{children}</div>}
    </section>
  );
}

export function Empty({ icon: Icon, text }: { icon: LucideIcon; text: string }) {
  return (
    <div className="empty">
      <Icon size={28} strokeWidth={1.5} />
      <span>{text}</span>
    </div>
  );
}
