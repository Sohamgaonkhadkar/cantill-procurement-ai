import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  PolicyDefinitionSchema,
  type PolicyResponse,
  type PolicyDefinition,
} from "@/api";
import { usePolicies } from "@/api/hooks";
import { useAuth } from "@/auth";
import { Page, Json, RunPicker, useRunSelection } from "@/components/Workflow";
import { Button, ErrorBlock, LoadingBlock } from "@/components/ui";
function definition(p: PolicyResponse): PolicyDefinition {
  return {
    version: p.version,
    effective_date: p.effective_date,
    parameters: p.parameters,
    rules: p.rules,
  };
}
function object(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}
export default function PolicyReactor() {
  const location = useLocation();
  const { identity } = useAuth();
  const admin = identity?.role === "admin";
  const policies = usePolicies();
  const registry = useQuery({
    queryKey: ["policy-registry"],
    queryFn: api.registry,
  });
  const selection = useRunSelection();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const selected =
    policies.data?.items.find((p) => p.version === selectedId) ??
    policies.data?.items.find((p) => p.status === "active") ??
    policies.data?.items[0];
  const [editor, setEditor] = useState("");
  const [version, setVersion] = useState("");
  const [effective, setEffective] = useState("2026-04-02");
  const [text, setText] = useState(() =>
    typeof location.state?.policyProposalText === "string"
      ? (location.state.policyProposalText as string)
      : "",
  );
  const [reason, setReason] = useState("");
  const [manual, setManual] = useState(false);
  const [precedenceAcknowledged, setPrecedenceAcknowledged] = useState(false);
  const [mappings, setMappings] = useState<
    Record<string, Record<string, string | boolean>>
  >({});
  const [priorityInput, setPriorityInput] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [ruleIndex, setRuleIndex] = useState(0);
  const [fact, setFact] = useState("requirement.plant");
  const [op, setOp] = useState("eq");
  const [value, setValue] = useState("");
  const [route, setRoute] = useState("RFQ");
  useEffect(() => {
    if (selected) {
      setEditor(JSON.stringify(definition(selected), null, 2));
      setRuleIndex(0);
      setManual(false);
      setPrecedenceAcknowledged(false);
      setMappings({});
      setResult(null);
    }
  }, [selected?.version]);
  const task = useMutation({
    mutationFn: (job: () => Promise<unknown>) => job(),
    onSuccess: (data) => {
      setResult(data);
      void qc.invalidateQueries();
    },
  });
  const gov = object(selected?.governance);
  const unsavedChanges =
    !!selected && editor !== JSON.stringify(definition(selected), null, 2);
  const interpretation = object(gov.interpretation);
  const unresolved = Array.isArray(interpretation.unresolved_clauses)
    ? interpretation.unresolved_clauses
    : [];
  const changes = Array.isArray(gov.diff) ? gov.diff.map(object) : [];
  const precedence = object(gov.precedence_analysis);
  const warnings = Array.isArray(precedence.warnings)
    ? precedence.warnings.map(object)
    : [];
  const reconciliationRows = unresolved.map(object).map((clause) => {
    const id = String(clause.id ?? "");
    const m = mappings[id] ?? {};
    return {
      clause_id: id,
      meaning: String(m.meaning ?? ""),
      scope: String(m.scope ?? ""),
      paths: String(m.paths ?? "")
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean),
      priority: m.priority ? Number(m.priority) : null,
      effective_date: String(
        m.effective_date || selected?.effective_date || "",
      ),
      evidence: String(m.evidence ?? ""),
      confirmed: m.confirmed === true,
    };
  });
  const mappingsReady = reconciliationRows.every(
    (m) =>
      m.clause_id &&
      m.meaning.length >= 10 &&
      m.scope.length >= 5 &&
      m.paths.length &&
      m.evidence.length >= 15 &&
      m.confirmed,
  );
  async function saveImported(promise: Promise<PolicyResponse>) {
    const p = await promise;
    qc.setQueryData<{ items: PolicyResponse[] }>(["policies"], (previous) => ({
      items: [
        ...(previous?.items.filter((item) => item.version !== p.version) ?? []),
        p,
      ],
    }));
    setSelectedId(p.version);
    setEditor(JSON.stringify(definition(p), null, 2));
    return p;
  }
  function parsed() {
    return PolicyDefinitionSchema.parse(JSON.parse(editor));
  }
  const locked = !admin || selected?.status !== "draft";
  const busy = task.isPending;
  return (
    <Page
      eyebrow="POLICY REACTOR · GOVERNED RULES"
      title="Change the rules. Keep the proof."
      lede="Rules are validated data. Inspect source, edit the exact DSL, simulate, review, approve and activate as separate actions."
    >
      {policies.error ? (
        <ErrorBlock error={policies.error} />
      ) : policies.isPending ? (
        <LoadingBlock />
      ) : null}
      {registry.error ? <ErrorBlock error={registry.error} /> : null}
      <div className="policy-layout">
        <aside className="surface-dark min-w-0 p-4">
          <h2 className="eyebrow mb-4">VERSION REGISTER</h2>
          <div className="space-y-2">
            {policies.data?.items.map((p) => (
              <button
                key={p.version}
                onClick={() => setSelectedId(p.version)}
                className={
                  "policy-version " +
                  (selected?.version === p.version ? "selected" : "")
                }
              >
                <span className="num break-all">{p.version}</span>
                <span>{p.status}</span>
                <small>Effective {p.effective_date}</small>
              </button>
            ))}
          </div>
        </aside>
        <section className="surface-dark min-w-0 p-5">
          {selected ? (
            <>
              <div className="toolbar">
                <h2 className="font-display text-2xl">{selected.version}</h2>
                <span className="num text-lime">{selected.status}</span>
              </div>
              <RuleCircuit
                policy={selected}
                selected={ruleIndex}
                onSelect={setRuleIndex}
              />
              <Json
                value={selected.rules[ruleIndex]}
                label="Selected rule / exact predicate"
              />
              <p className="mt-3 text-xs text-lavender">
                Lower priority executes first. The trace stops at the first
                matching rule.
              </p>
            </>
          ) : null}
        </section>
        <aside className="surface-dark min-w-0 space-y-4 p-5">
          <h2 className="font-display text-xl">Governance and source</h2>
          <p className="text-sm text-lavender">
            {selected?.status === "draft"
              ? "Drafts do not affect live processing."
              : "This version is immutable. Clone it into a new draft for changes."}
          </p>
          <p className="text-sm text-lavender" aria-live="polite">
            {unsavedChanges
              ? "Unsaved editor changes. Preview and save the draft before simulation, review or approval. These actions use the saved definition."
              : selected?.status === "draft"
                ? gov.reviewed
                  ? "Saved draft reviewed. Approve this definition, then activate it. Any further saved edit requires a new review."
                  : "Reconcile source clauses, preview and save edits, then simulate a selected run. Review the saved definition before approval and activation."
                : selected?.status === "approved"
                  ? "Approved definition ready for activation. Verify its effective date before activating."
                  : "Inspect the effective date and original source before creating an amendment."}
          </p>
          {unresolved.length ? (
            <div className="border border-coral p-4" role="alert">
              <strong className="text-coral">Unresolved source clauses</strong>
              <p className="mt-2 text-sm">
                Reconcile each clause in the DSL. Manual verification does not
                implement missing rules.
              </p>
              <Json value={unresolved} label="Unresolved clauses" />
              {unresolved.map(object).map((clause, index) => {
                const id = String(clause.id ?? "");
                const m = mappings[id] ?? {};
                return (
                  <fieldset
                    key={id || index}
                    className="mt-4 space-y-3 border border-lavender/30 p-3"
                  >
                    <legend>Clause {index + 1}</legend>
                    <p className="text-sm">{String(clause.text)}</p>
                    {!id ? (
                      <p role="alert">
                        Re-upload this legacy draft to assign stable clause IDs.
                      </p>
                    ) : null}
                    {(
                      [
                        ["meaning", "Intended meaning"],
                        ["scope", "Applicable scope"],
                        [
                          "paths",
                          "Changed DSL paths (comma separated, e.g. rules[rule-id])",
                        ],
                        [
                          "priority",
                          "Rule priority (leave blank for parameters)",
                        ],
                        ["effective_date", "Effective date (YYYY-MM-DD)"],
                        [
                          "evidence",
                          "Evidence: how the saved change implements this clause",
                        ],
                      ] as const
                    ).map(([key, label]) => (
                      <label className="field" key={key}>
                        {label}
                        <input
                          aria-label={`Clause ${index + 1} ${key}`}
                          value={String(
                            m[key] ??
                              (key === "effective_date"
                                ? selected?.effective_date
                                : "") ??
                              "",
                          )}
                          onChange={(e) =>
                            setMappings((previous) => ({
                              ...previous,
                              [id]: { ...previous[id], [key]: e.target.value },
                            }))
                          }
                        />
                      </label>
                    ))}
                    <label className="check-field">
                      <input
                        type="checkbox"
                        checked={m.confirmed === true}
                        onChange={(e) =>
                          setMappings((previous) => ({
                            ...previous,
                            [id]: {
                              ...previous[id],
                              confirmed: e.target.checked,
                            },
                          }))
                        }
                      />
                      I verified this clause against the saved executable
                      change.
                    </label>
                  </fieldset>
                );
              })}
            </div>
          ) : null}
          {warnings.length ? (
            <section
              className="border border-coral p-3"
              aria-label="Rule precedence warnings"
            >
              <h3>Possible rule shadowing</h3>
              <p className="text-sm">
                Symbolic overlaps require scope review and simulation; they are
                not actual purchasing decisions.
              </p>
              <ul className="list-disc pl-5">
                {warnings.map((warning, i) => (
                  <li key={i} className="mt-2 text-sm">
                    {String(warning.message)}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {precedence.requires_acknowledgement ? (
            <label className="check-field">
              <input
                aria-label="Acknowledge rule precedence"
                type="checkbox"
                checked={precedenceAcknowledged}
                onChange={(e) => setPrecedenceAcknowledged(e.target.checked)}
              />
              I reviewed precedence, including Capex, contract and emergency
              effects, and accept this ordering.
            </label>
          ) : null}
          <Json value={interpretation} label="Interpretation coverage" />
          <Json value={gov.source_text ?? ""} label="Original source text" />
          <Json value={gov} label="Governance history and diff" />
          {changes.length ? (
            <div
              className="overflow-x-auto"
              tabIndex={0}
              aria-label="Policy changes"
            >
              <table className="w-full text-left text-xs">
                <caption className="mb-2 text-left text-lime">
                  Saved changes from the base policy
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    <th scope="col">Before</th>
                    <th scope="col">After</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((change, i) => (
                    <tr
                      key={String(change.path) + i}
                      className="border-t border-lavender/20"
                    >
                      <th scope="row" className="max-w-40 break-words p-2 num">
                        {String(change.path)}
                      </th>
                      <td className="max-w-48 break-words p-2">
                        {JSON.stringify(change.before) ?? "Absent"}
                      </td>
                      <td className="max-w-48 break-words p-2">
                        {JSON.stringify(change.after) ?? "Absent"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <label className="field">
            Governance reason
            <textarea
              aria-label="Governance reason"
              minLength={5}
              maxLength={2000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {unresolved.length ? (
            <label className="check-field">
              <input
                type="checkbox"
                checked={manual}
                onChange={(e) => setManual(e.target.checked)}
              />
              I manually reconciled all unresolved clauses into the structured
              rules.
            </label>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {selected
              ? (["review", "approve", "activate", "deactivate"] as const).map(
                  (action) => (
                    <Button
                      key={action}
                      size="sm"
                      variant={action === "activate" ? "lime" : "ghost"}
                      busy={busy}
                      disabled={
                        !admin ||
                        unsavedChanges ||
                        reason.trim().length < 5 ||
                        (action === "review" &&
                          (selected.status !== "draft" ||
                            (unresolved.length > 0 &&
                              (!manual ||
                                !gov.structured_changes_saved ||
                                !mappingsReady)) ||
                            (!!precedence.requires_acknowledgement &&
                              !precedenceAcknowledged))) ||
                        (action === "approve" &&
                          (selected.status !== "draft" || !gov.reviewed)) ||
                        (action === "activate" &&
                          !["approved", "superseded"].includes(
                            selected.status,
                          )) ||
                        (action === "deactivate" &&
                          selected.status !== "active")
                      }
                      onClick={() =>
                        task.mutate(() =>
                          api.policyAction(
                            selected.version,
                            action,
                            reason,
                            manual,
                            {
                              precedence_acknowledged: precedenceAcknowledged,
                              reconciliations: reconciliationRows,
                            },
                          ),
                        )
                      }
                    >
                      {action[0].toUpperCase() + action.slice(1)} policy
                    </Button>
                  ),
                )
              : null}
          </div>
        </aside>
      </div>
      {selected ? (
        <section className="surface-dark space-y-5 p-6">
          <h2 className="font-display text-2xl">Structured policy editor</h2>
          <p className="text-lavender">
            Edit predicates, grouping windows, supplier counts and parameters.
            Draft edits clear prior review.
          </p>
          <label className="field">
            Policy DSL JSON
            <textarea
              aria-label="Policy DSL JSON"
              className="num"
              rows={18}
              value={editor}
              onChange={(e) => setEditor(e.target.value)}
              readOnly={locked}
            />
          </label>
          <div className="toolbar">
            <Button
              disabled={busy}
              onClick={() =>
                task.mutate(async () =>
                  api.previewPolicy(parsed(), selected.version),
                )
              }
            >
              Preview validation and diff
            </Button>
            <Button
              variant="lime"
              disabled={locked || busy}
              onClick={() =>
                task.mutate(async () => {
                  const p = await api.editPolicy(
                    parsed(),
                    String(gov.base_version ?? "5.0"),
                    String(gov.source_text ?? ""),
                  );
                  setEditor(JSON.stringify(definition(p), null, 2));
                  setManual(false);
                  setPrecedenceAcknowledged(false);
                  setMappings((previous) =>
                    Object.fromEntries(
                      Object.entries(previous).map(([id, entry]) => [
                        id,
                        { ...entry, confirmed: false },
                      ]),
                    ),
                  );
                  return p;
                })
              }
            >
              Save draft changes
            </Button>
          </div>
          <details>
            <summary>Add a registered-fact rule</summary>
            <div className="toolbar mt-4">
              <label className="field">
                Fact
                <select value={fact} onChange={(e) => setFact(e.target.value)}>
                  {Object.entries(registry.data?.facts ?? {}).map(([k, v]) => (
                    <option key={k} value={k}>
                      {k} ({v})
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Operator
                <select value={op} onChange={(e) => setOp(e.target.value)}>
                  {registry.data?.operators.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Value (strings or JSON lists)
                <input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                />
              </label>
              <label className="field">
                Route
                <select
                  value={route}
                  onChange={(e) => setRoute(e.target.value)}
                >
                  {registry.data?.routes.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <Button
                disabled={locked}
                onClick={() =>
                  task.mutate(async () => {
                    const p = parsed();
                    const priorities = new Set(p.rules.map((r) => r.priority));
                    const priority = Number(priorityInput);
                    if (
                      !priorityInput ||
                      !Number.isInteger(priority) ||
                      priorities.has(priority)
                    )
                      throw new Error(
                        "Choose an explicit unused integer priority. Lower numbers execute first; inspect precedence before review.",
                      );
                    const typedValue = ["in", "not_in"].includes(op)
                      ? JSON.parse(value)
                      : value === "true"
                        ? true
                        : value === "false"
                          ? false
                          : value;
                    p.rules.push({
                      id: "rule-" + Date.now(),
                      priority,
                      route:
                        route as PolicyDefinition["rules"][number]["route"],
                      when: { fact, op: op as "eq", value: typedValue },
                      reason: "Reviewed scoped rule",
                    });
                    const preview = await api.previewPolicy(
                      p,
                      selected.version,
                    );
                    setEditor(JSON.stringify(p, null, 2));
                    return preview;
                  })
                }
              >
                Add rule to editor
              </Button>
              <label className="field">
                Explicit priority
                <input
                  aria-label="New rule priority"
                  type="number"
                  value={priorityInput}
                  onChange={(e) => setPriorityInput(e.target.value)}
                />
              </label>
            </div>
          </details>
          <Json value={registry.data} label="Backend schema registry" />
        </section>
      ) : null}
      <section className="surface-dark space-y-5 p-6">
        <h2 className="font-display text-2xl">New amendment / draft</h2>
        <p className="text-lavender">
          Base version: {selected?.version ?? "—"}. Supply a unique version and
          effective date; the draft starts from the selected policy.
        </p>
        <div className="toolbar">
          <label className="field">
            New version
            <input
              aria-label="New policy version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="5.1-review"
            />
          </label>
          <label className="field">
            Effective date
            <input
              aria-label="Policy effective date"
              type="date"
              value={effective}
              onChange={(e) => setEffective(e.target.value)}
            />
          </label>
        </div>
        <label className="field">
          Amendment text
          <textarea
            aria-label="Amendment text"
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="If plant is CHK1 and category is Safety and value exceeds INR 75000 require RFQ"
          />
        </label>
        <div className="toolbar">
          <Button
            variant="lime"
            disabled={
              !admin ||
              !selected ||
              !version ||
              !effective ||
              !text.trim() ||
              busy
            }
            onClick={() =>
              task.mutate(() =>
                saveImported(
                  api.propose(text, version, effective, selected!.version),
                ),
              )
            }
          >
            Propose text amendment
          </Button>
          <Button
            disabled={!admin || !selected || !version || !effective || busy}
            onClick={() =>
              task.mutate(() =>
                saveImported(
                  api.createPolicy(
                    {
                      ...definition(selected!),
                      version,
                      effective_date: effective,
                    },
                    selected!.version,
                  ),
                ),
              )
            }
          >
            Clone selected as draft
          </Button>
          <label className="field">
            Upload amendment PDF / TXT / JSON
            <input
              aria-label="Upload amendment"
              type="file"
              accept=".pdf,.txt,.json"
              disabled={!admin || !selected || !version || !effective || busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  task.mutate(() =>
                    saveImported(
                      api.uploadAmendment(file, {
                        version,
                        effective_date: effective,
                        base_version: selected!.version,
                      }),
                    ),
                  );
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </section>
      <section className="surface-dark space-y-4 p-6">
        <h2 className="font-display text-2xl">
          Before / after batch simulation
        </h2>
        <RunPicker selection={selection} />
        <Button
          disabled={!selected || !selection.runId || busy || unsavedChanges}
          onClick={() =>
            task.mutate(() =>
              api.simulate(selected!.version, selection.runId, "calendar"),
            )
          }
        >
          Simulate selected policy
        </Button>
        <p className="text-sm text-lavender">
          Simulation uses the dated policy calendar: earlier requests retain
          their captured earlier policy. It does not activate the draft or
          reserve contract headroom. Batch Lab also provides pinned historical
          processing as a separate mode.
        </p>
      </section>
      {task.error ? <ErrorBlock error={task.error} /> : null}
      {result ? (
        <section className="surface-dark p-5" role="status">
          <h2 className="text-mint">Server result</h2>
          <Json
            value={result}
            label="Validation / simulation / governance result"
          />
        </section>
      ) : null}
    </Page>
  );
}
function RuleCircuit({
  policy,
  selected,
  onSelect,
}: {
  policy: PolicyResponse;
  selected: number;
  onSelect: (index: number) => void;
}) {
  const reduce = useReducedMotion();
  const routes = [...new Set(policy.rules.map((r) => r.route))];
  const height = Math.max(350, policy.rules.length * 95 + 40);
  return (
    <div className="policy-circuit grid-bg">
      <svg
        viewBox={`0 0 860 ${height}`}
        role="group"
        aria-label="Policy rule circuit"
        className="w-full"
      >
        {routes.map((route, i) => {
          const y = 40 + (i * (height - 100)) / Math.max(1, routes.length - 1);
          return (
            <g key={route}>
              <path
                d={`M 620 ${y} L 820 ${y} L 835 ${y + 15} L 835 ${y + 55} L 620 ${y + 55} Z`}
                fill="#141a42"
                stroke="#d7ff3f"
              />
              <text
                x="632"
                y={y + 31}
                fill="#d7ff3f"
                fontSize="13"
                fontFamily="monospace"
              >
                {route}
              </text>
            </g>
          );
        })}
        {policy.rules.map((r, i) => {
          const y = 30 + i * 95;
          const routeY =
            40 +
            (routes.indexOf(r.route) * (height - 100)) /
              Math.max(1, routes.length - 1) +
            28;
          return (
            <g key={r.id}>
              <motion.path
                d={`M 440 ${y + 30} C 530 ${y + 30}, 525 ${routeY}, 620 ${routeY}`}
                fill="none"
                stroke={selected === i ? "#d7ff3f" : "#8f7bff"}
                strokeWidth={selected === i ? 3 : 1}
                initial={reduce ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
              />
              <g
                role="button"
                tabIndex={0}
                aria-label={`Inspect rule ${r.id}`}
                onClick={() => onSelect(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelect(i);
                }}
                className="cursor-pointer"
              >
                <path
                  d={`M 30 ${y + 10} L 40 ${y} L 440 ${y} L 440 ${y + 50} L 430 ${y + 60} L 30 ${y + 60} Z`}
                  fill={selected === i ? "#2a1b8c" : "#141a42"}
                  stroke={selected === i ? "#d7ff3f" : "#8f7bff"}
                />
                <text x="45" y={y + 24} fill="#f5f3ec" fontSize="14">
                  {r.priority} · {r.id.slice(0, 35)}
                </text>
                <text x="45" y={y + 45} fill="#b7b3d7" fontSize="11">
                  {r.reason.slice(0, 55)}
                </text>
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
