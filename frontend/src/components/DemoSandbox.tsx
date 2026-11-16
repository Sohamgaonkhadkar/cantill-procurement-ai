import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/api";
import { Button, ErrorBlock, RouteTag } from "@/components/ui";
import { Json } from "@/components/Workflow";
import { downloadBlob } from "@/lib/csv";
import { formatMoney } from "@/lib/format";

export function DemoSandbox() {
  const [file, setFile] = useState<File | undefined>();
  const preview = useMutation({ mutationFn: () => api.demoPreview(file) });
  const input = useMutation({
    mutationFn: api.demoInput,
    onSuccess: (blob) => downloadBlob(blob, "synthetic-demo-input.csv"),
  });
  const output = useMutation({
    mutationFn: () => api.demoExport(file),
    onSuccess: (blob) => downloadBlob(blob, "synthetic-demo-decisions.csv"),
  });
  const busy = preview.isPending || input.isPending || output.isPending;
  return (
    <details className="surface-dark p-6 mb-6" data-testid="demo-sandbox">
      <summary className="cursor-pointer font-semibold text-lime">
        Try an isolated demo · fictional data
      </summary>
      <div className="mt-4 space-y-4">
        <p className="text-lavender text-sm leading-relaxed">
          Explore nine DEMO-prefixed requests using separate fictional items,
          suppliers and contracts under v5.0. Results are calculated by the
          procurement engine. They are not saved to the assessment workspace and
          do not affect its counters, policies or contract ceilings.
        </p>
        <div className="toolbar">
          <Button disabled={busy} onClick={() => input.mutate()}>
            Download demo input
          </Button>
          <Button
            disabled={busy}
            variant="lime"
            onClick={() => preview.mutate()}
          >
            Calculate demo
          </Button>
        </div>
        <label className="field">
          Demo CSV file (optional)
          <input
            aria-label="Demo CSV file (optional)"
            type="file"
            accept=".csv,text/csv"
            disabled={busy}
            onChange={(e) => {
              setFile(e.target.files?.[0]);
              preview.reset();
              output.reset();
            }}
          />
        </label>
        <p className="text-sm text-lavender">
          Download the demo input, edit quantities and upload it here to
          recalculate (up to 200 rows). Your ordinary Batch Lab upload below
          continues to use the assessment data.
        </p>
        {[preview.error, input.error, output.error]
          .filter(Boolean)
          .map((error, index) => (
            <ErrorBlock key={index} error={error} />
          ))}
        {preview.data ? (
          <>
            <p className="eyebrow text-mint">
              SYNTHETIC PREVIEW · NOT SAVED · POLICY{" "}
              {preview.data.policy_version}
            </p>
            <div className="toolbar">
              <span>
                {preview.data.result.rows.length} calculated{" "}
                {preview.data.result.rows.length === 1 ? "row" : "rows"} ·{" "}
                {preview.data.result.requirements.length}{" "}
                {preview.data.result.requirements.length === 1
                  ? "requirement"
                  : "requirements"}{" "}
                · {preview.data.result.issues.length}{" "}
                {preview.data.result.issues.length === 1 ? "issue" : "issues"}
              </span>
              <Button disabled={busy} onClick={() => output.mutate()}>
                Export demo decisions
              </Button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    {[
                      "Demo PR",
                      "Item",
                      "Value (INR)",
                      "Calculated route",
                      "Supplier / suggestions",
                    ].map((title) => (
                      <th key={title} className="p-3 text-left">
                        {title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.data.result.rows.map((row, index) => (
                    <tr key={index} className="border-t border-lavender/15">
                      <td className="p-3">{row.pr_no}</td>
                      <td className="p-3">{row.resolved_item_code}</td>
                      <td className="p-3 num">
                        {row.group_value_inr
                          ? formatMoney(row.group_value_inr)
                          : "—"}
                      </td>
                      <td className="p-3">
                        <RouteTag route={row.route} />
                      </td>
                      <td className="p-3">
                        {row.supplier_id || row.suggested_supplier_ids || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Json
              label="Computed demo evidence"
              value={preview.data.result.requirements}
            />
            {preview.data.result.issues.length ? (
              <Json
                label="Demo validation issues"
                value={preview.data.result.issues}
              />
            ) : null}
          </>
        ) : null}
      </div>
    </details>
  );
}
