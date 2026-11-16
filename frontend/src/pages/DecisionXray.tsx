import { useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { useRequests } from "@/api/hooks";
import {
  Page,
  RunPicker,
  useRunSelection,
  Json,
  Pagination,
} from "@/components/Workflow";
import { Button, ErrorBlock, LoadingBlock, RouteTag } from "@/components/ui";
import { XRayScene, type XPlate, type ViewState } from "@/components/XRayScene";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { formatMoney } from "@/lib/format";
const TITLES = [
  "ITEM RESOLUTION",
  "REQUIREMENT GROUPING",
  "VALUATION",
  "POLICY EVALUATION",
  "FINAL ROUTE",
];
export default function DecisionXray() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const selection = useRunSelection();
  const [paging, setPaging] = useState({ runId: "", offset: 0 });
  const offset = paging.runId === selection.runId ? paging.offset : 0;
  const setOffset = (value: number) =>
    setPaging({ runId: selection.runId, offset: value });
  const requests = useRequests({
    run_id: selection.runId || undefined,
    limit: 25,
    offset,
  });
  const pick = requestId ?? requests.data?.items[0]?.id;
  const req = useQuery({
    queryKey: ["requirement", selection.runId, pick],
    queryFn: () => api.requirement(pick!, selection.runId),
    enabled: !!pick && !!selection.runId,
  });
  const [stage, setStage] = useState(0);
  const [twoD, setTwoD] = useState(false);
  const view = useRef<ViewState>({ yaw: 0, pitch: 0 });
  const drag = useRef<{
    x: number;
    y: number;
    yaw: number;
    pitch: number;
  } | null>(null);
  const r = req.data;
  const e = r?.evidence;
  const plates: XPlate[] = r
    ? [
        { title: TITLES[0], value: r.item_code, sub: r.description },
        {
          title: TITLES[1],
          value: r.id,
          sub: `${r.lines.length} PR lines · ${r.quantity} units`,
        },
        {
          title: TITLES[2],
          value: formatMoney(r.group_value_inr),
          sub: e!.valuation.source,
        },
        {
          title: TITLES[3],
          value: r.policy_version,
          sub: e!.rule_trace
            .filter((x) => x.matched)
            .map((x) => String(x.rule))
            .join(", "),
        },
        { title: TITLES[4], value: r.route, sub: r.approval_status },
      ]
    : TITLES.map((title) => ({ title, value: "AWAITING TRACE", sub: "—" }));
  return (
    <Page
      eyebrow="DECISION X-RAY · IMMUTABLE EVIDENCE"
      title="Inspect the machine."
      lede="Matching, grouping, exact valuation and policy evidence come from the stored procurement run."
    >
      <RunPicker
        selection={{
          ...selection,
          setRunId: (value) =>
            navigate(`/decision-xray?run_id=${encodeURIComponent(value)}`),
        }}
      />
      <div className="trace-chooser surface-dark toolbar p-4">
        <label className="field">
          Trace requirement
          <select
            aria-label="Trace requirement"
            value={pick ?? ""}
            onChange={(event) =>
              navigate(
                `/decision-xray/${encodeURIComponent(event.target.value)}?run_id=${encodeURIComponent(selection.runId)}`,
              )
            }
          >
            {pick && !requests.data?.items.some((item) => item.id === pick) ? (
              <option value={pick}>
                {r?.item_code ?? "Requirement"} · {pick}
              </option>
            ) : null}
            {requests.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.item_code} · {item.id} · {item.route}
              </option>
            ))}
          </select>
        </label>
        <Pagination
          page={requests.data}
          pending={requests.isFetching}
          onChange={setOffset}
        />
      </div>
      {requests.error ? <ErrorBlock error={requests.error} /> : null}
      {req.error ? (
        <ErrorBlock error={req.error} />
      ) : req.isFetching && !r ? (
        <LoadingBlock />
      ) : !r ? (
        <p>No requirement selected.</p>
      ) : (
        <>
          <div className="toolbar">
            <RouteTag route={r.route} />
            <span className="num">
              {r.approval_status} · {r.id}
            </span>
            <Button size="sm" onClick={() => setTwoD(!twoD)}>
              {twoD ? "3D machine" : "2D evidence"}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                view.current = { yaw: 0, pitch: 0 };
              }}
            >
              Reset view
            </Button>
          </div>
          <div className="xray-layout">
            <section className="min-w-0">
              <div className="toolbar">
                {TITLES.map((t, i) => (
                  <Button
                    key={t}
                    size="sm"
                    variant={stage === i ? "lime" : "ghost"}
                    onClick={() => setStage(i)}
                  >
                    {i + 1} · {t}
                  </Button>
                ))}
              </div>
              {!twoD ? (
                <div
                  className="xray-canvas grid-bg"
                  onPointerDown={(event) => {
                    drag.current = {
                      x: event.clientX,
                      y: event.clientY,
                      ...view.current,
                    };
                    event.currentTarget.setPointerCapture(event.pointerId);
                  }}
                  onPointerMove={(event) => {
                    if (drag.current)
                      view.current = {
                        yaw: Math.max(
                          -0.55,
                          Math.min(
                            0.55,
                            drag.current.yaw +
                              (event.clientX - drag.current.x) * 0.004,
                          ),
                        ),
                        pitch: Math.max(
                          -0.3,
                          Math.min(
                            0.3,
                            drag.current.pitch +
                              (event.clientY - drag.current.y) * 0.003,
                          ),
                        ),
                      };
                  }}
                  onPointerUp={() => {
                    drag.current = null;
                  }}
                >
                  <XRayScene
                    plates={plates}
                    selected={stage}
                    route={
                      r.decision === "PO"
                        ? "direct"
                        : r.decision === "SOURCING_REQUEST"
                          ? "sourcing"
                          : null
                    }
                    view={view}
                    onSelect={setStage}
                    runId={0}
                  />
                </div>
              ) : null}
              <div className="surface-dark mt-4 p-5">
                <h2 className="font-display text-xl">{TITLES[stage]}</h2>
                <p className="mt-2">
                  {plates[stage].value} · {plates[stage].sub}
                </p>
                <Json
                  label="Stage evidence"
                  value={
                    [
                      e!.matching,
                      {
                        anchor: e!.group_anchor,
                        grouping: e!.grouping,
                        lines: r.lines,
                      },
                      e!.valuation,
                      { facts: e!.facts, rule_trace: e!.rule_trace },
                      {
                        route: r.route,
                        reason: r.reason,
                        supplier: r.supplier_id,
                        order_reference: e!.order_reference,
                        selected_contract: e!.selected_contract,
                        po_anchor: e!.po_anchor,
                      },
                    ][stage]
                  }
                />
              </div>
              <div className="paper-texture mt-5 p-5 text-ink">
                <h2 className="font-display text-xl">Contract evaluation</h2>
                <p className="my-3 text-sm">
                  Exact remaining headroom and rejection reasons at processing
                  time.
                </p>
                <Json value={e!.contracts} label="All evaluated contracts" />
                <h2 className="font-display mt-5 text-xl">
                  Supplier selection
                </h2>
                <Json
                  value={e!.ranking}
                  label="Ranking components and reference prices"
                />
                <p className="mt-3">
                  PO reference price: {formatMoney(r.unit_price)}. Valuation:{" "}
                  {formatMoney(e!.valuation.unit_price)} from{" "}
                  {e!.valuation.reference}.
                </p>
              </div>
            </section>
            <aside className="min-w-0 space-y-5">
              <div className="surface-dark p-5">
                <h2 className="font-display text-xl">Decision explanation</h2>
                <p className="mt-3 leading-relaxed text-lavender">{r.reason}</p>
                <p className="num mt-4">
                  Exact group value {formatMoney(e!.valuation.exact_value)}
                </p>
              </div>
              <ApprovalPanel
                key={selection.runId + r.id}
                requirement={r}
                runId={selection.runId}
              />
              <Json value={r} label="Complete structured decision" />
            </aside>
          </div>
        </>
      )}
    </Page>
  );
}
