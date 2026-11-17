import { useState } from "react";
import { useQueryClient, useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { api, type ChatResponse } from "@/api";
import { useMasters } from "@/api/hooks";
import { ProductVisual } from "@/components/media/ProductVisual";
import { PageHeading, Button, ErrorBlock, RouteTag } from "@/components/ui";
import { Json, traceUrl } from "@/components/Workflow";
import { formatMoney } from "@/lib/format";
export default function RequestStudio() {
  const qc = useQueryClient();
  const [input, setInput] = useState("");
  const [fictionalAcknowledged, setFictionalAcknowledged] = useState(false);
  const ai = useQuery({ queryKey: ["ai-status"], queryFn: api.aiStatus });
  const [chat, setChat] = useState<ChatResponse | null>(
    () => qc.getQueryData<ChatResponse>(["chat-current"]) ?? null,
  );
  const masters = useMasters();
  const send = useMutation({
    mutationFn: (message: string) =>
      api.chat(message, chat?.session_id, {
        request_id: crypto.randomUUID(),
        expected_revision: chat?.revision ?? 0,
        action:
          message === "confirm"
            ? "confirm"
            : message === "cancel"
              ? "cancel"
              : "message",
        demo_data_acknowledged: fictionalAcknowledged,
      }),
    onSuccess: (data) => {
      setChat(data);
      qc.setQueryData(["chat-current"], data);
      setInput("");
      if (data.run) void qc.invalidateQueries();
    },
  });
  const state = chat?.state ?? {};
  const item = masters.data?.items.find((i) => i.item_code === state.item_code);
  const ready = state.ready === true;
  const messages = chat?.messages ?? [];
  return (
    <div className="grid min-h-[calc(100vh-68px)] grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(340px,43%)]">
      <section className="min-w-0 p-6 md:p-10">
        <PageHeading
          eyebrow="REQUEST STUDIO · CONVERSATIONAL INTAKE"
          title="Start with what you need."
          lede="Describe your request. Inspect the specification, correct it and confirm before creating a PR."
        />
        <div className="chat-privacy-note mt-5" role="status">
          <strong>
            {ai.data?.external_eligible
              ? ai.data.configuration_status === "configured"
                ? "Gemini · fictional demo only"
                : "Gemini key required · local mode active"
              : "Local procurement assistant"}
          </strong>
          <p>
            Purchasing decisions are calculated by the deterministic engine.
            Source references identify the records used in an answer.
          </p>
          {ai.data?.external_eligible ? (
            <label className="check-field mt-3">
              <input
                type="checkbox"
                checked={fictionalAcknowledged}
                onChange={(e) => setFictionalAcknowledged(e.target.checked)}
              />
              I confirm that my messages contain only fictional demo data. Allow
              Gemini to process them.
            </label>
          ) : (
            <p>
              Live records and private documents stay within this workspace.
              External AI is disabled.
            </p>
          )}
        </div>
        <div className="mt-8 space-y-4" aria-live="polite">
          {messages.length ? (
            messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={
                  m.role === "user" ? "chat-message user" : "chat-message"
                }
              >
                <span className="eyebrow">{String(m.role)}</span>
                <p className="mt-2 whitespace-pre-wrap">{String(m.content)}</p>
                {Array.isArray(m.citations) && m.citations.length ? (
                  <div className="source-cards">
                    {m.citations.map((raw, j) => {
                      const source = raw as Record<string, unknown>;
                      return (
                        <details key={j}>
                          <summary>
                            {String(source.title)}
                            {source.clause ? " · " + String(source.clause) : ""}
                            {source.page
                              ? " · page " + String(source.page)
                              : ""}
                          </summary>
                          <p className="whitespace-pre-wrap">
                            {String(source.excerpt)}
                          </p>
                          <small>
                            Version{" "}
                            {String(source.policy_version ?? "record snapshot")}{" "}
                            · {String(source.content_hash).slice(0, 12)}
                          </small>
                        </details>
                      );
                    })}
                  </div>
                ) : null}
              </motion.div>
            ))
          ) : (
            <div className="chat-message text-lavender">
              Tell me the item or specification, quantity, plant, need-by date
              and whether this is Normal or Emergency.
            </div>
          )}
        </div>
        {chat ? (
          <p className="mt-3 text-sm text-lavender">
            {chat.ai_status === "available"
              ? chat.mode === "intake"
                ? "Gemini-assisted intake · server-validated draft"
                : "Gemini answer · source-checked"
              : chat.ai_status === "local_only"
                ? "Local response · no external model call"
                : chat.ai_status === "disabled"
                  ? "Deterministic intake"
                  : chat.ai_status === "invalid_answer_local_fallback"
                    ? "Gemini's answer could not be verified. Answering from workspace records instead."
                    : chat.ai_status === "local_evidence"
                      ? "Answered from workspace records. These sources are kept local."
                      : "Gemini is unavailable right now. Using the local procurement assistant instead."}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          {typeof state.policy_proposal_text === "string" ? (
            <Link
              className="button"
              to="/policy-reactor"
              state={{ policyProposalText: state.policy_proposal_text }}
            >
              Review policy proposal
            </Link>
          ) : null}
          {chat?.alternatives.map((a, i) => (
            <Button
              key={i}
              size="sm"
              busy={send.isPending}
              onClick={() => send.mutate(String(a.item_code))}
            >
              {String(a.item_code)} · {String(a.description)}
            </Button>
          ))}
        </div>
        <form
          className="surface-dark mt-6 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim()) send.mutate(input.trim());
          }}
        >
          <label className="field">
            Describe the request
            <textarea
              aria-label="Describe the request"
              rows={3}
              maxLength={4000}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe an item, quantity, plant, need-by date and urgency"
            />
          </label>
          <div className="flex flex-wrap justify-between gap-3">
            <Button
              type="button"
              disabled={!chat || send.isPending}
              onClick={() => send.mutate("cancel")}
            >
              Reset draft
            </Button>
            <Button
              type="submit"
              variant="lime"
              busy={send.isPending}
              disabled={!input.trim()}
            >
              Send
            </Button>
          </div>
        </form>
        {send.error ? (
          <div className="mt-4">
            <ErrorBlock error={send.error} />
          </div>
        ) : null}
        {chat?.run ? (
          <div className="surface-dark mt-6 p-5" role="status">
            <h2 className="text-mint">
              {chat.run.issues.length
                ? "Request needs correction"
                : "PR created"}
            </h2>
            <p className="num mt-2">{chat.run.id}</p>
            {chat.run.issues.length ? (
              <Json value={chat.run.issues} label="Validation issues" />
            ) : (
              chat.run.requirements.map((r) => (
                <div key={r.id} className="mt-3">
                  <RouteTag route={r.route} />
                  <p>{r.reason}</p>
                  <Link
                    className="text-lime underline"
                    to={traceUrl(r, chat.run!.id)}
                  >
                    Inspect decision evidence
                  </Link>
                </div>
              ))
            )}
          </div>
        ) : null}
      </section>
      <section className="min-w-0 space-y-6 border-l border-lavender/10 p-6 md:p-10">
        <ProductVisual
          className="h-[310px] w-full"
          category={item?.category}
          itemCode={item?.item_code ?? String(state.item_code ?? "")}
          itemName={item?.description ?? String(state.description ?? "")}
          facts={[
            { label: "UOM", value: String(state.uom ?? item?.uom ?? "—") },
            { label: "PLANT", value: String(state.plant ?? "—") },
          ]}
        />
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="paper-texture p-7 text-ink"
        >
          <div className="eyebrow">
            REQUISITION / {chat?.session_id ?? "NEW DRAFT"}
          </div>
          <h2 className="font-display my-4 text-[27px]">
            {ready
              ? "Ready for your confirmation"
              : "Specification in progress"}
          </h2>
          <dl className="spec-list">
            {[
              ["Item", item?.description ?? state.item_code],
              ["Quantity", state.quantity],
              ["Unit", state.uom ?? item?.uom],
              ["Plant", state.plant],
              ["Need by", state.need_by_date],
              ["Urgency", state.urgency],
              [
                "Estimated unit price",
                state.estimated_unit_price
                  ? formatMoney(String(state.estimated_unit_price))
                  : "—",
              ],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt>{String(label)}</dt>
                <dd>{String(value ?? "Unresolved")}</dd>
              </div>
            ))}
          </dl>
          <Button
            variant="ink"
            className="mt-6 w-full"
            disabled={!ready || send.isPending}
            busy={send.isPending}
            onClick={() => send.mutate("confirm")}
          >
            Confirm and create PR
          </Button>
          <p className="mt-3 text-xs">
            Creation occurs only after confirmation and server validation.
          </p>
        </motion.div>
        {masters.error ? (
          <ErrorBlock error={masters.error} />
        ) : (
          <Json value={masters.data?.plants} label="Available plants" />
        )}
      </section>
    </div>
  );
}
