import type { ReactNode } from "react";
/** A readable rendering of server evidence; never derives financial values. */
export function EvidenceView({
  value,
  depth = 0,
}: {
  value: unknown;
  depth?: number;
}): ReactNode {
  if (value === null || value === undefined)
    return <span className="text-lavender">Not recorded</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (typeof value !== "object")
    return <span className="evidence-value">{String(value)}</span>;
  if (depth > 4)
    return (
      <details>
        <summary>Additional detail</summary>
        <pre>{JSON.stringify(value, null, 2)}</pre>
      </details>
    );
  if (Array.isArray(value))
    return value.length ? (
      <div className="evidence-array">
        {value.map((entry, i) => (
          <div key={i} className="evidence-entry">
            <EvidenceView value={entry} depth={depth + 1} />
          </div>
        ))}
      </div>
    ) : (
      <p className="text-lavender">No records in this stage.</p>
    );
  return (
    <dl className="evidence-fields">
      {Object.entries(value as Record<string, unknown>).map(([key, entry]) => (
        <div key={key}>
          <dt>{key.replace(/_/g, " ")}</dt>
          <dd>
            <EvidenceView value={entry} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
