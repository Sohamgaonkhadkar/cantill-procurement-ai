import type { ReactNode } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useState } from "react";
import { useRuns } from "@/api/hooks";
import type { PageOf, RequirementResponse } from "@/api";
import { PageHeading, Button, ErrorBlock, LoadingBlock, RouteTag } from "./ui";
import { formatMoney, formatDate } from "@/lib/format";
export function Page({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede?: string;
  children: ReactNode;
}) {
  return (
    <div className="workflow-page">
      <PageHeading eyebrow={eyebrow} title={title} lede={lede} />
      <div className="mt-8 space-y-6">{children}</div>
    </div>
  );
}
export function Json({
  value,
  label = "Structured evidence",
}: {
  value: unknown;
  label?: string;
}) {
  return (
    <details className="json-details">
      <summary>{label}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
export function Pagination({
  page,
  onChange,
  pending = false,
}: {
  page?: PageOf<unknown>;
  onChange: (offset: number) => void;
  pending?: boolean;
}) {
  if (!page) return null;
  return (
    <div className="pagination">
      <span>
        {page.total
          ? `${page.offset + 1}–${Math.min(page.offset + page.limit, page.total)}`
          : "0"}{" "}
        of {page.total}
      </span>
      <Button
        size="sm"
        disabled={pending || page.offset === 0}
        onClick={() => onChange(Math.max(0, page.offset - page.limit))}
      >
        Previous
      </Button>
      <Button
        size="sm"
        disabled={pending || page.offset + page.limit >= page.total}
        onClick={() => onChange(page.offset + page.limit)}
      >
        Next
      </Button>
    </div>
  );
}
export function useRunSelection() {
  const [params, setParams] = useSearchParams();
  const [offset, setOffset] = useState(0);
  const runs = useRuns(offset);
  const runId = params.get("run_id") ?? runs.data?.items[0]?.id ?? "";
  return {
    runs,
    runId,
    setRunId: (value: string) =>
      setParams((previous) => {
        previous.set("run_id", value);
        return previous;
      }),
    setOffset,
  };
}
export function RunPicker({
  selection,
}: {
  selection: ReturnType<typeof useRunSelection>;
}) {
  const { runs, runId, setRunId, setOffset } = selection;
  return (
    <div className="surface-dark p-4 space-y-3">
      <label className="field">
        Processing run
        <select
          aria-label="Processing run"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
        >
          {runId && !runs.data?.items.some((x) => x.id === runId) ? (
            <option value={runId}>{runId}</option>
          ) : null}
          {runs.data?.items.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id} · {r.line_count} lines ·{" "}
              {r.explicit_policy ?? "dated policy"}
            </option>
          ))}
        </select>
      </label>
      {runs.isPending ? (
        <LoadingBlock rows={1} />
      ) : runs.error ? (
        <ErrorBlock error={runs.error} onRetry={() => runs.refetch()} />
      ) : null}
      <div className="toolbar">
        <Button
          size="sm"
          busy={runs.isFetching}
          onClick={() => void runs.refetch()}
        >
          Refresh runs
        </Button>
        <Pagination page={runs.data} onChange={setOffset} />
      </div>
    </div>
  );
}
export function traceUrl(r: RequirementResponse, runId: string) {
  return `/decision-xray/${encodeURIComponent(r.id)}?run_id=${encodeURIComponent(runId)}`;
}
export function RequirementsTable({
  items,
  runId,
}: {
  items: RequirementResponse[];
  runId: string;
}) {
  return (
    <div className="paper-texture table-wrap">
      <table>
        <thead>
          <tr>
            <th>Requirement / PR lines</th>
            <th>Item</th>
            <th>Quantity</th>
            <th>Plant / need by</th>
            <th>Route</th>
            <th>Group value</th>
            <th>Status</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={String(r.record_id ?? r.id)}>
              <td className="num">
                {r.id}
                <div className="text-xs text-ink-2">
                  {r.lines.map((l) => `${l.pr_no}:${l.pr_line}`).join(", ")}
                </div>
              </td>
              <td>
                {r.item_code}
                <div className="max-w-[260px] text-xs">{r.description}</div>
              </td>
              <td className="num">{r.quantity}</td>
              <td>
                {r.plant}
                <div>{formatDate(r.need_by_date)}</div>
              </td>
              <td>
                <RouteTag tone="paper" route={r.route} />
              </td>
              <td className="num">{formatMoney(r.group_value_inr)}</td>
              <td>{r.approval_status}</td>
              <td>
                <Link className="text-ultra underline" to={traceUrl(r, runId)}>
                  Inspect
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 ? (
        <p className="p-6">No requirements match this selection.</p>
      ) : null}
    </div>
  );
}
