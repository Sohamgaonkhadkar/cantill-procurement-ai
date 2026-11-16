import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ROUTES } from "@/api";
import { useRequests } from "@/api/hooks";
import {
  Page,
  RunPicker,
  useRunSelection,
  RequirementsTable,
  Pagination,
} from "@/components/Workflow";
import { ErrorBlock, LoadingBlock } from "@/components/ui";
import { ApprovalPanel } from "@/components/ApprovalPanel";
export default function BuyerInbox() {
  const selection = useRunSelection();
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("pending");
  const [route, setRoute] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const rows = useRequests({
    run_id: selection.runId || undefined,
    status,
    route,
    search,
    offset,
  });
  const pick =
    rows.data?.items.find((x) => x.id === selected) ?? rows.data?.items[0];
  const detail = useQuery({
    queryKey: ["requirement", selection.runId, pick?.id],
    queryFn: () => api.requirement(pick!.id, selection.runId),
    enabled: !!pick && !!selection.runId,
  });
  return (
    <Page
      eyebrow="BUYER INBOX · WORK LEDGER"
      title="Decide, then move on."
      lede="Review one processing run at a time. Recommendations are separate from committed purchasing actions."
    >
      <RunPicker selection={selection} />
      <div className="toolbar">
        <label className="field">
          Status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setOffset(0);
            }}
          >
            {["pending", "approved", "overridden", ""].map((x) => (
              <option key={x} value={x}>
                {x || "All statuses"}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Route
          <select
            value={route}
            onChange={(e) => {
              setRoute(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All routes</option>
            {ROUTES.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Search items / plant
          <input
            value={search}
            maxLength={200}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </label>
      </div>
      <div className="inbox-layout">
        <section className="min-w-0">
          {rows.isPending ? (
            <LoadingBlock />
          ) : rows.error ? (
            <ErrorBlock error={rows.error} onRetry={() => rows.refetch()} />
          ) : (
            <>
              <RequirementsTable
                items={rows.data?.items ?? []}
                runId={selection.runId}
              />
              <Pagination page={rows.data} onChange={setOffset} />
            </>
          )}
        </section>
        <aside className="min-w-0 space-y-5">
          <label className="field">
            Inspect requirement
            <select
              aria-label="Inspect requirement"
              value={pick?.id ?? ""}
              onChange={(e) => setSelected(e.target.value)}
            >
              {rows.data?.items.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.item_code} · {r.id}
                </option>
              ))}
            </select>
          </label>
          {detail.error ? (
            <ErrorBlock error={detail.error} />
          ) : detail.data ? (
            <ApprovalPanel
              key={selection.runId + detail.data.id}
              requirement={detail.data}
              runId={selection.runId}
            />
          ) : null}
        </aside>
      </div>
    </Page>
  );
}
