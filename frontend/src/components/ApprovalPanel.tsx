import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RequirementResponse } from "@/api";
import { useAction } from "@/api/hooks";
import { useAuth } from "@/auth";
import { Button, ErrorBlock } from "./ui";
export function ApprovalPanel({
  requirement: r,
  runId,
}: {
  requirement: RequirementResponse;
  runId: string;
}) {
  const { identity } = useAuth();
  const [reason, setReason] = useState("");
  const [route, setRoute] = useState("RFQ");
  const [ack, setAck] = useState(false);
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId),
    enabled: !!runId && identity?.role !== "requester",
  });
  const action = useAction((kind: "approve" | "override") =>
    kind === "approve"
      ? api.approve(r.id, runId, reason)
      : api.override(r.id, runId, route, reason),
  );
  if (identity?.role === "requester")
    return (
      <p className="text-lavender">
        A buyer must review and approve this recommendation.
      </p>
    );
  if (r.approval_status !== "pending")
    return (
      <div role="status">
        Current status: {r.approval_status}
        {r.action_id ? " · " + String(r.action_id) : ""}
      </div>
    );
  const scope = r.po_id
    ? run.data?.orders.find((o) => o.id === r.po_id)?.requirements
    : [r.id];
  return (
    <section className="surface-dark space-y-4 p-5" aria-label="Buyer actions">
      <h2 className="font-display text-xl">Review before committing</h2>
      <p className="text-sm text-lavender">
        {r.decision === "PO"
          ? `Approval commits all pending requirements on consolidated PO ${r.po_id}. Contract headroom is rechecked atomically.`
          : "Approval creates an internal sourcing request. No supplier invitation is sent."}
      </p>
      <p className="num break-words text-xs">
        Planned scope:{" "}
        {Array.isArray(scope)
          ? scope.join(", ")
          : "Loading consolidated scope…"}
      </p>
      {run.error ? <ErrorBlock error={run.error} /> : null}
      <label className="field">
        Buyer reason
        <textarea
          aria-label="Buyer reason"
          maxLength={2000}
          minLength={5}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
        />
      </label>
      <label className="check-field">
        <input
          type="checkbox"
          checked={ack}
          onChange={(e) => setAck(e.target.checked)}
        />
        I reviewed the evidence and approval scope.
      </label>
      <Button
        variant="lime"
        disabled={
          reason.trim().length < 5 ||
          !ack ||
          !scope ||
          r.route === "NOT_PROCESSED"
        }
        busy={action.isPending}
        onClick={() => action.mutate("approve")}
      >
        Approve recommendation
      </Button>
      <div className="border-t border-lavender/20 pt-4">
        <label className="field">
          Override to sourcing
          <select
            aria-label="Override to sourcing"
            value={route}
            onChange={(e) => setRoute(e.target.value)}
          >
            {["RFQ", "RFP", "CAPEX_SOURCING", "NEW_ITEM_SOURCING"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <Button
          variant="danger"
          disabled={reason.trim().length < 5 || !ack}
          busy={action.isPending}
          onClick={() => action.mutate("override")}
        >
          Override to sourcing
        </Button>
      </div>
      {action.error ? <ErrorBlock error={action.error} /> : null}
      {action.data ? (
        <p role="status" className="text-mint">
          Recorded {action.data.id}
        </p>
      ) : null}
    </section>
  );
}
