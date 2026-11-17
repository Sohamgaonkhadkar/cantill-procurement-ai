import { useState } from "react";

const labels: Record<string, string> = {
  pr_no: "Purchase request",
  pr_line: "Line",
  item_code: "Item code",
  supplier_id: "Supplier",
  group_value_inr: "Group value (INR)",
  exact_value: "Exact value (INR)",
  unit_price: "Unit price (INR)",
  reference_price: "Reference price (INR)",
  po_id: "Planned purchase order",
  when: "Conditions",
  rule_trace: "Policy rule checks",
  matched: "Matched",
  selected_contract: "Selected contract",
  order_reference: "Price reference",
  po_anchor: "PO consolidation anchor",
  source_hash: "Source fingerprint",
};
export function evidenceLabel(key: string) {
  return (
    labels[key] ??
    key
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/[_.]/g, " ")
      .replace(/^./, (c) => c.toUpperCase())
  );
}
function scalar(value: unknown) {
  if (value === null || value === undefined || value === "")
    return "Not applicable / not supplied";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
export function EvidenceView({
  value,
  depth = 0,
}: {
  value: unknown;
  depth?: number;
}) {
  const [limit, setLimit] = useState(20);
  if (Array.isArray(value)) {
    if (!value.length)
      return <p className="evidence-empty">No records for this section.</p>;
    const records = value.slice(0, limit);
    const objects = records.every(
      (v) => v && typeof v === "object" && !Array.isArray(v),
    );
    const keys = objects
      ? [...new Set(records.flatMap((v) => Object.keys(v as object)))]
      : [];
    const tabular =
      objects &&
      keys.length <= 7 &&
      records.every((v) =>
        Object.values(v as object).every(
          (x) => x === null || typeof x !== "object",
        ),
      );
    return (
      <div className="evidence-collection">
        {tabular ? (
          <div
            className="evidence-table-wrap"
            tabIndex={0}
            role="region"
            aria-label="Evidence records"
          >
            <table className="evidence-table">
              <thead>
                <tr>
                  {keys.map((k) => (
                    <th key={k} scope="col">
                      {evidenceLabel(k)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((v, i) => (
                  <tr key={i}>
                    {keys.map((k) => (
                      <td key={k}>
                        {scalar((v as Record<string, unknown>)[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <ol className="evidence-records">
            {records.map((v, i) => (
              <li key={i}>
                <EvidenceView value={v} depth={depth + 1} />
              </li>
            ))}
          </ol>
        )}
        {value.length > limit ? (
          <button
            className="evidence-more"
            type="button"
            onClick={() => setLimit((n) => n + 20)}
          >
            Show more records ({limit} of {value.length} shown)
          </button>
        ) : null}
      </div>
    );
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length)
      return <p className="evidence-empty">No fields supplied.</p>;
    return (
      <dl className={"evidence-fields" + (depth ? " evidence-nested" : "")}>
        {entries.map(([key, v]) => (
          <div key={key}>
            <dt>{evidenceLabel(key)}</dt>
            <dd>
              {v && typeof v === "object" && depth >= 2 ? (
                <details>
                  <summary>Inspect {evidenceLabel(key).toLowerCase()}</summary>
                  <EvidenceView value={v} depth={depth + 1} />
                </details>
              ) : (
                <EvidenceView value={v} depth={depth + 1} />
              )}
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  return <span className="evidence-value">{scalar(value)}</span>;
}
