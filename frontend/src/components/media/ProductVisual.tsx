import { useState, type CSSProperties } from "react";
import { cn } from "@/utils/cn";
import { visualForCategory } from "./assets";
type Props = {
  category: string | null | undefined;
  itemCode?: string | null;
  itemName?: string | null;
  confidence?: number | null;
  facts?: { label: string; value: string }[];
  className?: string;
  compact?: boolean;
  style?: CSSProperties;
};
export function ProductVisual({
  category,
  itemCode,
  itemName,
  facts = [],
  className,
  style,
}: Props) {
  const [failed, setFailed] = useState(false);
  const asset = visualForCategory(category);
  return (
    <figure className={cn("product-reference", className)} style={style}>
      {asset && !failed ? (
        <img
          src={asset.src}
          alt={asset.alt}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="product-reference-empty">
          <span className="eyebrow">{category || "Item specification"}</span>
          <p>
            {itemCode
              ? "No verified catalog photograph supplied."
              : "Choose an exact catalog specification."}
          </p>
        </div>
      )}
      <figcaption>
        <small>
          {asset && !failed
            ? "Material family illustration · not a catalog SKU photograph"
            : "Catalog record"}
        </small>
        <strong>{itemCode || "Awaiting item resolution"}</strong>
        <p>
          {itemName ||
            "The backend will resolve your specification before a request is created."}
        </p>
        {facts.length ? (
          <dl>
            {facts.map((f) => (
              <div key={f.label}>
                <dt>{f.label}</dt>
                <dd>{f.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </figcaption>
    </figure>
  );
}
