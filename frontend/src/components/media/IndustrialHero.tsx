import type { RefObject } from "react";
import { Link } from "react-router-dom";
import { useOverview, usePolicies } from "@/api/hooks";
import { ErrorBlock, LoadingBlock } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { HERO_POSTER } from "./assets";

export function IndustrialHero({
  scrollRef: _scrollRef,
}: {
  scrollRef: RefObject<HTMLElement | null>;
}) {
  const overview = useOverview(),
    policies = usePolicies();
  const today = new Date().toLocaleDateString("en-CA", {
    timeZone: "Asia/Kolkata",
  });
  const active = policies.data?.items
    .filter((p) => p.status === "active" && p.effective_date <= today)
    .sort((a, b) => b.effective_date.localeCompare(a.effective_date))[0];
  const metrics = overview.data;
  return (
    <section className="industrial-hero">
      <div className="hero-editorial-grid">
        <div className="hero-editorial-copy">
          <div className="eyebrow">Corvo / Procurement operations</div>
          <h1>
            PROCUREMENT,
            <br />
            <em>with a reason.</em>
          </h1>
          <p>
            From the first requirement to an accountable decision. Match
            precisely. Apply policy. Keep the evidence.
          </p>
          <div className="hero-actions">
            <Link to="/request-studio">New purchase request ↗</Link>
            <Link to="/batch-lab">Process batch</Link>
          </div>
          <p className="eyebrow">
            {active
              ? `Policy ${active.version} · Effective ${formatDate(active.effective_date)}`
              : "Reading effective policy…"}
          </p>
        </div>
        <figure className="hero-photo">
          <img
            src={HERO_POSTER.src}
            alt={HERO_POSTER.alt}
            fetchPriority="high"
          />
          <figcaption className="hero-photo-caption">
            01 / Precision in the workshop. Clarity in procurement.
          </figcaption>
        </figure>
      </div>
      {overview.error ? (
        <ErrorBlock error={overview.error} />
      ) : overview.isPending ? (
        <LoadingBlock label="Reading live metrics" rows={1} />
      ) : (
        <div className="hero-metrics">
          {[
            {
              label: "Awaiting review",
              value: metrics?.pending_requirements,
              to: "/inbox",
              action: "Review queue",
            },
            {
              label: "Approved orders",
              value: metrics?.purchase_orders,
              to: "/purchase-orders",
              action: "Inspect orders",
            },
            {
              label: "Sourcing records",
              value: metrics?.sourcing_requests,
              to: "/sourcing",
              action: "Open sourcing",
            },
            {
              label: "Effective policy",
              value: active?.version,
              to: "/policy-reactor",
              action: "Inspect rules",
            },
          ].map((m) => (
            <div className="hero-metric" key={m.label}>
              <small>{m.label}</small>
              <strong>{m.value ?? "—"}</strong>
              <Link to={m.to}>{m.action} ↗</Link>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
