import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion } from "motion/react";
import { api } from "@/api";
import { useMasters, usePolicies } from "@/api/hooks";
import { Page, Pagination, Json } from "@/components/Workflow";
import { Button, LoadingBlock, ErrorBlock, Spotlight } from "@/components/ui";
import { ProductVisual } from "@/components/media/ProductVisual";
import { downloadBlob } from "@/lib/csv";
import { formatMoney } from "@/lib/format";
export default function SupplierConstellation() {
  const masters = useMasters();
  const policies = usePolicies();
  const [item, setItem] = useState("");
  const [date, setDate] = useState(
    new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
  );
  const [version, setVersion] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const itemCode = item || masters.data?.items[0]?.item_code || "";
  const ranking = useQuery({
    queryKey: ["suppliers", date, itemCode, offset, version],
    queryFn: () => api.suppliers(date, itemCode, offset, version),
    enabled: !!itemCode && !!date,
  });
  const list = ranking.data?.items ?? [];
  const selected = list.find((s) => s.supplier_id === selectedId) ?? list[0];
  const catalog = masters.data?.items.find((i) => i.item_code === itemCode);
  const download = useMutation({
    mutationFn: () => api.exportSuppliers(date, version),
    onSuccess: (b) => downloadBlob(b, "preferred-suppliers.csv"),
  });
  return (
    <Page
      eyebrow="SUPPLIER CONSTELLATION · RESEARCH VIEW"
      title="Who can deliver, and how well."
      lede="Eligibility and component scores are calculated by the backend for the selected catalog item and as-of date."
    >
      <div className="toolbar">
        <label className="field">
          Catalog item
          <select
            aria-label="Supplier item"
            value={itemCode}
            onChange={(e) => {
              setItem(e.target.value);
              setOffset(0);
              setSelectedId("");
            }}
          >
            {masters.data?.items.map((i) => (
              <option key={i.item_code} value={i.item_code}>
                {i.item_code} · {i.description}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          As of
          <input
            aria-label="Supplier as-of date"
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label className="field">
          Ranking policy
          <select
              aria-label="Supplier ranking policy"
            value={version}
            onChange={(e) => {
              setVersion(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Automatic dated policy</option>
            {policies.data?.items
              .filter((p) => ["active", "superseded"].includes(p.status))
              .map((p) => (
                <option key={p.version}>{p.version}</option>
              ))}
          </select>
        </label>
        <Button busy={download.isPending} onClick={() => download.mutate()}>
          Export preferred CSV
        </Button>
      </div>
      {masters.error ? <ErrorBlock error={masters.error} /> : null}
      {download.error ? <ErrorBlock error={download.error} /> : null}
      {ranking.isPending ? (
        <LoadingBlock />
      ) : ranking.error ? (
        <ErrorBlock error={ranking.error} onRetry={() => ranking.refetch()} />
      ) : (
        <>
          <div className="supplier-layout">
            <Spotlight className="surface-dark min-w-0 p-5">
              <svg
                viewBox="0 0 820 500"
                className="w-full"
                role="group"
                aria-label="Supplier constellation: delivery percentage and quality rating"
              >
                <defs>
                  <radialGradient id="sc-node">
                    <stop offset="0" stopColor="#f5f3ec" />
                    <stop offset="1" stopColor="#32e6d2" />
                  </radialGradient>
                </defs>
                {[0, 25, 50, 75, 100].map((v) => (
                  <g key={v}>
                    <line
                      x1={75 + v * 6.8}
                      x2={75 + v * 6.8}
                      y1="30"
                      y2="420"
                      stroke="#b7b3d7"
                      strokeOpacity=".15"
                    />
                    <text
                      x={75 + v * 6.8}
                      y="447"
                      fill="#b7b3d7"
                      fontSize="13"
                      textAnchor="middle"
                    >
                      {v}%
                    </text>
                  </g>
                ))}
                {[0, 1, 2, 3, 4, 5].map((v) => (
                  <g key={v}>
                    <line
                      x1="75"
                      x2="755"
                      y1={420 - v * 75}
                      y2={420 - v * 75}
                      stroke="#b7b3d7"
                      strokeOpacity=".15"
                    />
                    <text x="50" y={425 - v * 75} fill="#b7b3d7" fontSize="13">
                      {v}
                    </text>
                  </g>
                ))}
                <text x="350" y="485" fill="#b7b3d7" fontSize="13">
                  ON-TIME DELIVERY (%)
                </text>
                <text
                  transform="translate(20 290) rotate(-90)"
                  fill="#b7b3d7"
                  fontSize="13"
                >
                  QUALITY / 5
                </text>
                {list.map((s, i) => {
                  const master = masters.data?.suppliers.find(
                    (m) => m.supplier_id === s.supplier_id,
                  );
                  if (!master) return null;
                  const x = 75 + Number(master.on_time_pct) * 6.8;
                  const y = 420 - Number(master.quality_rating) * 75;
                  return (
                    <g
                      key={s.supplier_id}
                      role="button"
                      tabIndex={0}
                      aria-label={`Select supplier ${s.supplier_id}`}
                      onClick={() => setSelectedId(s.supplier_id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") setSelectedId(s.supplier_id);
                      }}
                    >
                      <motion.circle
                        cx={x}
                        cy={y}
                        r={8 + Math.sqrt(s.purchase_count) * 2}
                        fill="url(#sc-node)"
                        stroke={
                          selected?.supplier_id === s.supplier_id
                            ? "#d7ff3f"
                            : "#32e6d2"
                        }
                        strokeWidth="2"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.04 }}
                      />
                      <title>
                        {s.name} · {master.on_time_pct}% on time · quality{" "}
                        {master.quality_rating}/5 · rank {s.rank}
                      </title>
                      {selected?.supplier_id === s.supplier_id ? (
                        <text
                          x={Math.min(700, x)}
                          y={Math.max(22, y - 25)}
                          fill="#d7ff3f"
                          fontSize="13"
                          textAnchor="middle"
                        >
                          {s.supplier_id} · RANK {s.rank}
                        </text>
                      ) : null}
                    </g>
                  );
                })}
              </svg>
              <p className="text-xs text-lavender">
                Node size = qualifying purchase count. Every plotted value comes
                from the supplier master. Select a row if nodes coincide.
              </p>
            </Spotlight>
            <aside className="surface-dark min-w-0 space-y-4 p-5">
              <ProductVisual
                category={catalog?.category}
                itemCode={catalog?.item_code}
                itemName={catalog?.description}
                className="h-[210px]"
              />
              {selected ? (
                <>
                  <h2 className="font-display text-2xl">{selected.name}</h2>
                  <p className="num text-mint">
                    Rank {selected.rank} · score {selected.score}
                  </p>
                  <p>Reference price {formatMoney(selected.reference_price)}</p>
                  <p className="text-sm text-lavender">
                    {selected.reference_source} · {selected.purchase_count}{" "}
                    qualifying purchases · last{" "}
                    {selected.last_purchase ?? "none"}
                  </p>
                  <Json
                    value={selected.components}
                    label="Weighted score components"
                  />
                  <Json value={selected} label="Complete ranking evidence" />
                </>
              ) : (
                <p>No eligible suppliers for this item and date.</p>
              )}
            </aside>
          </div>
          <div className="paper-texture table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Supplier</th>
                  <th>Score</th>
                  <th>Purchases</th>
                  <th>Reference price</th>
                  <th>Reference source</th>
                </tr>
              </thead>
              <tbody>
                {list.map((s) => (
                  <tr key={s.supplier_id}>
                    <td>{s.rank}</td>
                    <td>
                      <button
                        className="text-ultra underline"
                        onClick={() => setSelectedId(s.supplier_id)}
                      >
                        {s.supplier_id} · {s.name}
                      </button>
                    </td>
                    <td>{s.score}</td>
                    <td>{s.purchase_count}</td>
                    <td>{formatMoney(s.reference_price)}</td>
                    <td>{s.reference_source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={ranking.data} onChange={setOffset} />
        </>
      )}
    </Page>
  );
}
