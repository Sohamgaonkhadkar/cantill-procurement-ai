import { EvidenceView } from "@/components/EvidenceView";
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { motion } from "motion/react";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Page, Pagination, Json } from "@/components/Workflow";
import { Button, ErrorBlock, LoadingBlock } from "@/components/ui";
import { formatMoney } from "@/lib/format";
export default function ContractVault() {
  const { contractId } = useParams();
  const { identity } = useAuth();
  const buyer = identity?.role !== "requester";
  const [offset, setOffset] = useState(0);
  const [asOf, setAsOf] = useState(
    new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
  );
  const [selectedId, setSelectedId] = useState("");
  const [editor, setEditor] = useState("");
  const [reason, setReason] = useState("");
  const [ack, setAck] = useState(false);
  const qc = useQueryClient();
  const contracts = useQuery({
    queryKey: ["contracts", offset, asOf],
    queryFn: () => api.contracts(offset, asOf),
  });
  const proposals = useQuery({
    queryKey: ["contract-proposals"],
    queryFn: api.proposals,
    enabled: buyer,
  });
  const proposal =
    proposals.data?.items.find((p) => p.id === selectedId) ??
    proposals.data?.items.find((p) => p.status === "pending_review");
  const detail = useQuery({
    queryKey: ["contract", contractId, asOf],
    enabled: !!contractId,
    queryFn: () => api.contract(contractId!, asOf),
  });
  useEffect(() => {
    if (proposal) {
      setEditor(
        JSON.stringify(
          proposal.contract ?? {
            contract_id: "",
            supplier_id: "",
            start_date: "",
            end_date: "",
            value_cap: "0",
            consumed_value: "0",
            lines: [{ item_code: "", uom: "", rate: "0" }],
          },
          null,
          2,
        ),
      );
      setAck(false);
    }
  }, [proposal?.id]);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadContract(file),
    onSuccess: (p) => {
      setSelectedId(p.id);
      void qc.invalidateQueries({ queryKey: ["contract-proposals"] });
    },
  });
  const approve = useMutation({
    mutationFn: () =>
      api.approveContract(proposal!.id, JSON.parse(editor), reason),
    onSuccess: () => {
      setAck(false);
      setReason("");
      void qc.invalidateQueries();
    },
  });
  return (
    <Page
      eyebrow="CONTRACT VAULT · TECHNICAL RECORDS"
      title="Every agreement, under inspection."
      lede="Register values include committed approvals. Uploads remain proposals until a buyer verifies and approves the structured terms."
    >
      <div className="toolbar">
        <label className="field">
          Contract as-of date
          <input
            type="date"
            value={asOf}
            onChange={(e) => {
              setAsOf(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        {buyer ? (
          <label className="field">
            Upload contract PDF
            <input
              aria-label="Upload contract PDF"
              type="file"
              accept=".pdf,application/pdf"
              disabled={upload.isPending}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
                e.target.value = "";
              }}
            />
          </label>
        ) : null}
      </div>
      {upload.error ? <ErrorBlock error={upload.error} /> : null}
      {upload.isPending ? (
        <LoadingBlock label="Extracting contract proposal" rows={1} />
      ) : null}
      {contractId ? (
        <section className="surface-dark p-5">
          <Link className="text-lime underline" to="/contracts">
            Back to register
          </Link>
          {detail.error ? (
            <ErrorBlock error={detail.error} />
          ) : detail.data ? (
            <>
              <EvidenceView value={detail.data} />
              <Json value={detail.data} label="Contract terms and provenance" />
            </>
          ) : (
            <LoadingBlock />
          )}
        </section>
      ) : null}
      {contracts.error ? (
        <ErrorBlock error={contracts.error} />
      ) : contracts.isPending ? (
        <LoadingBlock />
      ) : (
        <>
          <div className="contract-library">
            {contracts.data?.items.map((c, i) => (
              <motion.div
                key={c.contract_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.025 }}
                className="paper-texture contract-tile"
              >
                <div
                  className={
                    c.valid_as_of ? "contract-spine active" : "contract-spine"
                  }
                />
                <div className="min-w-0 space-y-4 p-5">
                  <div className="toolbar">
                    <Link
                      to={"/contracts/" + encodeURIComponent(c.contract_id)}
                      className="num text-ultra underline"
                    >
                      {c.contract_id}
                    </Link>
                    <span className="text-xs">
                      {c.valid_as_of ? "VALID AS OF DATE" : "OUTSIDE VALIDITY"}
                    </span>
                  </div>
                  <h2 className="font-display text-2xl">{c.supplier_id}</h2>
                  <p>
                    {c.start_date} → {c.end_date}
                  </p>
                  <dl className="spec-list">
                    <div>
                      <dt>Value cap</dt>
                      <dd>{formatMoney(c.value_cap)}</dd>
                    </div>
                    <div>
                      <dt>Consumed</dt>
                      <dd>{formatMoney(c.consumed_value)}</dd>
                    </div>
                    <div>
                      <dt>Committed</dt>
                      <dd>{formatMoney(c.committed_value)}</dd>
                    </div>
                    <div>
                      <dt>Remaining</dt>
                      <dd>{formatMoney(c.remaining_value)}</dd>
                    </div>
                  </dl>
                  <Json
                    value={c.lines}
                    label={`${c.lines.length} contract line(s)`}
                  />
                </div>
              </motion.div>
            ))}
          </div>
          <Pagination page={contracts.data} onChange={setOffset} />
        </>
      )}
      {buyer ? (
        <section className="surface-dark space-y-5 p-6">
          <h2 className="font-display text-2xl">Proposal inspection</h2>
          {proposals.error ? <ErrorBlock error={proposals.error} /> : null}
          <label className="field">
            Contract proposal
            <select
              aria-label="Contract proposal"
              value={proposal?.id ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {proposals.data?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.status}
                </option>
              ))}
            </select>
          </label>
          {proposal ? (
            <>
              <p className="num break-all text-xs">
                Original PDF SHA256: {proposal.source_hash}
              </p>
              <p className="text-copper">
                Signature authenticity is not cryptographically verified.
                Confirm the original document yourself.
              </p>
              {proposal.validation_error ? (
                <div role="alert" className="text-coral">
                  {proposal.validation_error}
                </div>
              ) : null}
              <details open>
                <summary>Extracted source text</summary>
                <p className="contract-source">
                  {proposal.source_text ||
                    "No readable source text was extracted. Manual transcription is required."}
                </p>
              </details>
              <label className="field">
                Verified contract JSON
                <textarea
                  aria-label="Verified contract JSON"
                  rows={12}
                  className="num"
                  value={editor}
                  onChange={(e) => setEditor(e.target.value)}
                  readOnly={proposal.status !== "pending_review"}
                />
              </label>
              <label className="field">
                Contract verification reason
                <textarea
                  aria-label="Contract verification reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  minLength={5}
                  maxLength={2000}
                />
              </label>
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                />
                I checked supplier, items, units, rates, dates and ceiling
                against the original agreement.
              </label>
              <Button
                variant="lime"
                busy={approve.isPending}
                disabled={
                  !ack ||
                  reason.trim().length < 5 ||
                  proposal.status !== "pending_review"
                }
                onClick={() => approve.mutate()}
              >
                Approve verified contract
              </Button>
              {approve.error ? (
                <ErrorBlock error={approve.error} />
              ) : approve.data ? (
                <p role="status" className="text-mint">
                  Contract {approve.data.contract_id} persisted.
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-lavender">No uploaded proposals.</p>
          )}
        </section>
      ) : null}
    </Page>
  );
}
