import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { Page, Pagination, Json } from "@/components/Workflow";
import { Button, ErrorBlock, LoadingBlock, RouteTag } from "@/components/ui";
import { formatMoney } from "@/lib/format";
export function PurchaseOrders() {
  return <Actions kind="purchase-orders" />;
}
export function Sourcing() {
  return <Actions kind="sourcing" />;
}
function Actions({ kind }: { kind: "purchase-orders" | "sourcing" }) {
  const [offset, setOffset] = useState(0);
  const [id, setId] = useState("");
  const records = useQuery({
    queryKey: [kind, offset],
    queryFn: () => api.actions(kind, offset),
  });
  const detail = useQuery({
    queryKey: [kind, "detail", id],
    queryFn: () => api.action(kind, id),
    enabled: !!id,
  });
  return (
    <Page
      eyebrow={
        kind === "purchase-orders"
          ? "PURCHASE ORDERS · APPROVED RECORDS"
          : "SOURCING · APPROVED RECORDS"
      }
      title={
        kind === "purchase-orders"
          ? "Approved, recorded, traceable."
          : "Competition starts with evidence."
      }
      lede="These are committed internal records. Recommendations and simulations are shown separately in Batch Lab; no external dispatch is implied."
    >
      {records.isPending ? (
        <LoadingBlock />
      ) : records.error ? (
        <ErrorBlock error={records.error} />
      ) : (
        <>
          <div className="paper-texture table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Processing run</th>
                  <th>Requirements</th>
                  <th>Approved by</th>
                  <th>Approved at</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {records.data?.items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <button
                        className="text-ultra underline"
                        onClick={() => setId(a.id)}
                      >
                        {a.id}
                      </button>
                    </td>
                    <td className="num">{a.run_id}</td>
                    <td>{a.requirements.length}</td>
                    <td>{a.actor}</td>
                    <td>{a.approved_at}</td>
                    <td>{a.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!records.data?.total ? (
              <p className="p-6">No approved records yet.</p>
            ) : null}
          </div>
          <Pagination page={records.data} onChange={setOffset} />
        </>
      )}
      {id ? (
        <section className="surface-dark p-5">
          <Button size="sm" onClick={() => setId("")}>
            Close detail
          </Button>
          {detail.error ? (
            <ErrorBlock error={detail.error} />
          ) : detail.data ? (
            <>
              <h2 className="font-display mt-4 text-2xl">{detail.data.id}</h2>
              <p className="mt-3">{detail.data.reason}</p>
              {detail.data.recommendations.map((r) => (
                <div
                  key={r.id}
                  className="mt-4 space-y-2 border-t border-lavender/20 pt-4"
                >
                  <RouteTag route={r.route} />
                  <p>
                    {r.description} · quantity {r.quantity} · group valuation{" "}
                    {formatMoney(r.group_value_inr)} · order reference price{" "}
                    {formatMoney(r.unit_price)}
                  </p>
                  <Link
                    className="text-lime underline"
                    to={`/decision-xray/${r.id}?run_id=${encodeURIComponent(detail.data!.run_id)}`}
                  >
                    Open original decision
                  </Link>
                  <Json value={r} label="Recommendation evidence" />
                </div>
              ))}
              <Json value={detail.data} label="Full committed action" />
            </>
          ) : (
            <LoadingBlock />
          )}
        </section>
      ) : null}
    </Page>
  );
}
export function AuditTrail() {
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState("");
  const events = useQuery({
    queryKey: ["audit", offset, action],
    queryFn: () => api.audit(offset, action),
  });
  return (
    <Page
      eyebrow="AUDIT TRAIL · PERSISTED EVENTS"
      title="Every action leaves a record."
      lede="Actual actor, timestamps and stored details. Filter by an exact event action."
    >
      <label className="field max-w-md">
        Audit action filter
        <input
          aria-label="Audit action filter"
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setOffset(0);
          }}
          placeholder="policy.approved"
        />
      </label>
      {events.error ? (
        <ErrorBlock error={events.error} />
      ) : events.isPending ? (
        <LoadingBlock />
      ) : (
        <>
          <div className="surface-dark divide-y divide-lavender/15">
            {events.data?.items.map((e) => (
              <article key={e.id} className="p-5">
                <div className="toolbar">
                  <span className="num text-mint">{e.action}</span>
                  <span>{e.actor}</span>
                  <time className="num text-xs text-lavender">
                    {e.created_at}
                  </time>
                </div>
                <Json value={e.details} label="Event details" />
              </article>
            ))}
            {!events.data?.total ? (
              <p className="p-6">No matching audit events.</p>
            ) : null}
          </div>
          <Pagination page={events.data} onChange={setOffset} />
        </>
      )}
    </Page>
  );
}
