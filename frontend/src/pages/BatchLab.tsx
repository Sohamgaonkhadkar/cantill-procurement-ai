import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type RunResponse } from "@/api";
import { usePolicies } from "@/api/hooks";
import {
  Page,
  RunPicker,
  useRunSelection,
  Json,
  RequirementsTable,
} from "@/components/Workflow";
import { Button, ErrorBlock, LoadingBlock, RouteTag } from "@/components/ui";
import { IndustrialImage } from "@/components/media/IndustrialImage";
import { VISUALS } from "@/components/media/assets";
import { parseCsv, downloadBlob } from "@/lib/csv";
export const INPUT_HEADERS = [
  "pr_no",
  "pr_line",
  "created_at",
  "requester",
  "department",
  "plant",
  "item_code",
  "description",
  "quantity",
  "uom",
  "estimated_unit_price",
  "need_by_date",
  "urgency",
];
export const OUTPUT_HEADERS = [
  "pr_no",
  "pr_line",
  "resolved_item_code",
  "group_id",
  "po_id",
  "decision",
  "route",
  "supplier_id",
  "unit_price",
  "group_value_inr",
  "suggested_supplier_ids",
  "policy_version",
  "reason",
];
export default function BatchLab() {
  const selection = useRunSelection();
  const qc = useQueryClient();
  const policies = usePolicies();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string[][]>([]);
  const [fileError, setFileError] = useState<unknown>(null);
  const [version, setVersion] = useState("5.0");
  const [local, setLocal] = useState<RunResponse | null>(null);
  const [other, setOther] = useState("");
  const [page, setPage] = useState(0);
  const existing = useQuery({
    queryKey: ["run", selection.runId],
    queryFn: () => api.run(selection.runId),
    enabled: !!selection.runId,
  });
  const run = local?.id === selection.runId ? local : existing.data;
  const process = useMutation({
    mutationFn: () => api.processBatch(file!, version),
    onSuccess: (r) => {
      setLocal(r);
      selection.setRunId(r.id);
      setPage(0);
      comparison.reset();
      void qc.invalidateQueries();
    },
  });
  const replay = useMutation({ mutationFn: () => api.replay(run!.id) });
  const download = useMutation({
    mutationFn: () => api.exportRun(run!.id),
    onSuccess: (blob) => downloadBlob(blob, `${run!.id}.csv`),
  });
  const comparison = useMutation({
    mutationFn: async () => {
      const right = await api.run(other);
      if (right.input_hash !== run!.input_hash)
        throw new Error(
          "Choose two runs with identical input hashes for a policy comparison.",
        );
      return api.compare(run!.id, other);
    },
  });
  useEffect(() => {
    replay.reset();
    comparison.reset();
    download.reset();
    setPage(0);
  }, [selection.runId]);
  async function load(f?: File) {
    if (!f) return;
    setFile(null);
    setFileError(null);
    setPreview([]);
    try {
      if (!f.name.toLowerCase().endsWith(".csv"))
        throw new Error("Choose a CSV file.");
      if (f.size > 10 * 1024 * 1024)
        throw new Error(
          "Maximum upload is 10 MiB; hosted platform limits may be lower.",
        );
      const parsed = parseCsv((await f.text()).replace(/^\uFEFF/, ""));
      const missing = INPUT_HEADERS.filter((h) => !parsed[0]?.includes(h));
      if (missing.length)
        throw new Error("Missing CSV headers: " + missing.join(", "));
      if (parsed.length < 2) throw new Error("CSV contains no data rows.");
      setPreview(parsed.slice(0, 6));
      setFile(f);
    } catch (e) {
      setFileError(e);
    }
  }
  return (
    <Page
      eyebrow="BATCH LAB · REPRODUCIBLE PROCESSING"
      title="Raw lines. Controlled outcomes."
      lede="Process real CSV data, inspect every issue, replay immutable snapshots and export the authoritative 13-column result."
    >
      <div className="batch-upload-layout">
        <section className="surface-dark p-6">
          <label className="field">
            PR CSV file
            <input
              aria-label="PR CSV file"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => void load(e.target.files?.[0])}
            />
          </label>
          <label className="field">
            Policy version
            <select
              aria-label="Batch policy version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            >
              <option value="">Automatic dated selection</option>
              {policies.data?.items
                .filter((p) => p.status !== "draft" && p.status !== "approved")
                .map((p) => (
                  <option key={p.version}>{p.version}</option>
                ))}
            </select>
          </label>
          <Button
            variant="lime"
            disabled={!file}
            busy={process.isPending}
            onClick={() => process.mutate()}
          >
            Process batch
          </Button>
          <Button
            className="ml-3"
            onClick={() =>
              downloadBlob(
                new Blob([INPUT_HEADERS.join(",") + "\n"], {
                  type: "text/csv",
                }),
                "pr-template.csv",
              )
            }
          >
            Download input template
          </Button>
          {fileError ? <ErrorBlock error={fileError} /> : null}
          {process.error ? <ErrorBlock error={process.error} /> : null}
          <Json label="Required input headers" value={INPUT_HEADERS} />
          {preview.length ? (
            <Json label="CSV preview (first five data rows)" value={preview} />
          ) : null}
        </section>
        <IndustrialImage
          className="h-full min-h-[260px] w-full"
          asset={VISUALS.gears}
          grade="violet"
        />
      </div>
      <RunPicker selection={selection} />
      {existing.error ? (
        <ErrorBlock error={existing.error} />
      ) : !run ? (
        <LoadingBlock label="Reading stored run" />
      ) : (
        <>
          <div className="toolbar">
            <span className="num break-all">{run.id}</span>
            <Button busy={download.isPending} onClick={() => download.mutate()}>
              Export exact CSV
            </Button>
            <Button busy={replay.isPending} onClick={() => replay.mutate()}>
              Replay snapshot
            </Button>
          </div>
          {download.error ? <ErrorBlock error={download.error} /> : null}
          {replay.error ? (
            <ErrorBlock error={replay.error} />
          ) : replay.data ? (
            <p
              role="status"
              className={replay.data.matches ? "text-mint" : "text-coral"}
            >
              Replay{" "}
              {replay.data.matches
                ? "matches original output"
                : "differs from original output"}{" "}
              · {replay.data.output_hash}
            </p>
          ) : null}
          <div className="toolbar">
            {Object.entries(run.counts).map(([route, count]) => (
              <span key={route}>
                <RouteTag route={route} /> <span className="num">{count}</span>
              </span>
            ))}
          </div>
          <p>
            {run.rows.length} output lines · {run.requirements.length}{" "}
            requirements · {run.issues.length} invalid lines. Planned orders
            have not been approved.
          </p>
          <Json value={run.issues} label="All validation issues" />
          <div className="paper-texture table-wrap">
            <table>
              <thead>
                <tr>
                  {OUTPUT_HEADERS.map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {run.rows.slice(page * 25, (page + 1) * 25).map((r, i) => (
                  <tr key={i}>
                    {OUTPUT_HEADERS.map((h) => (
                      <td key={h} className="num">
                        {String(r[h] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              Lines {page * 25 + 1}–{Math.min((page + 1) * 25, run.rows.length)}{" "}
              of {run.rows.length}
            </span>
            <Button disabled={!page} onClick={() => setPage(page - 1)}>
              Previous lines
            </Button>
            <Button
              disabled={(page + 1) * 25 >= run.rows.length}
              onClick={() => setPage(page + 1)}
            >
              Next lines
            </Button>
          </div>
          <Json
            value={{
              input_hash: run.input_hash,
              output_hash: run.output_hash,
              data_hash: run.data_hash,
              policy_hash: run.policy_hash,
            }}
            label="Snapshot hashes"
          />
          <details>
            <summary>Requirements and decision traces</summary>
            <RequirementsTable items={run.requirements} runId={run.id} />
          </details>
          <section className="surface-dark p-5">
            <h2 className="font-display text-xl">Before / after comparison</h2>
            <label className="field">
              Compare with run ID
              <input
                aria-label="Compare with run ID"
                value={other}
                onChange={(e) => setOther(e.target.value)}
                placeholder="RUN-…"
              />
            </label>
            <Button
              disabled={!other || other === run.id}
              busy={comparison.isPending}
              onClick={() => comparison.mutate()}
            >
              Compare runs
            </Button>
            {comparison.error ? (
              <ErrorBlock error={comparison.error} />
            ) : comparison.data ? (
              <>
                <p className="mt-4" role="status">
                  {comparison.data.affected_lines} affected lines ·{" "}
                  {comparison.data.explanation_changes} explanation changes
                </p>
                <Json
                  value={comparison.data.changes}
                  label="Exact before / after values"
                />
              </>
            ) : null}
          </section>
        </>
      )}
    </Page>
  );
}
