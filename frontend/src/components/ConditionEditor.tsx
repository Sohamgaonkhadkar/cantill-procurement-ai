import { useEffect, useState } from "react";
import { Button } from "./ui";
type Condition = Record<string, unknown>;
const predicate = () => ({ fact: "requirement.plant", op: "eq", value: "" });
function TypedValue({
  value,
  type,
  op,
  onChange,
  disabled,
}: {
  value: unknown;
  type: string;
  op: string;
  onChange: (v: unknown) => void;
  disabled: boolean;
}) {
  const serialize = (v: unknown) =>
    typeof v === "string" ? v : JSON.stringify(v);
  const [text, setText] = useState(serialize(value));
  useEffect(() => setText(serialize(value)), [value]);
  const list = ["in", "not_in"].includes(op);
  if (["boolean", "bool"].includes(type) && !list)
    return (
      <select
        aria-label="Predicate value"
        disabled={disabled}
        value={String(value)}
        onChange={(e) => onChange(e.target.value === "true")}
      >
        <option value="true">True</option>
        <option value="false">False</option>
      </select>
    );
  return (
    <input
      aria-label="Predicate value"
      type={type === "date" && !list ? "date" : "text"}
      inputMode={
        ["decimal", "number", "money"].includes(type) ? "decimal" : undefined
      }
      value={text ?? ""}
      disabled={disabled}
      placeholder={list ? 'JSON list, e.g. ["A", "B"]' : "Value"}
      onChange={(e) => setText(e.target.value)}
      onBlur={(e) => {
        try {
          let result: unknown = text;
          if (list) {
            result = JSON.parse(text);
            if (!Array.isArray(result)) throw Error("Use a JSON list");
          } else if (type === "integer") {
            if (!/^\d+$/.test(text)) throw Error("Use an integer");
            result = Number(text);
          } else if (
            ["number", "decimal", "money", "Decimal"].includes(type) &&
            !/^[-+]?\d+(\.\d+)?$/.test(text)
          )
            throw Error("Use an exact decimal value");
          e.currentTarget.setCustomValidity("");
          onChange(result);
        } catch {
          e.currentTarget.setCustomValidity(
            "Enter a value matching " + (list ? "a JSON list" : type),
          );
          e.currentTarget.reportValidity();
        }
      }}
    />
  );
}
export function ConditionEditor({
  value,
  facts,
  operators,
  disabled,
  onChange,
  depth = 0,
}: {
  value: unknown;
  facts: Record<string, string>;
  operators: string[];
  disabled: boolean;
  onChange: (v: Condition) => void;
  depth?: number;
}) {
  const condition = (
    value && typeof value === "object" ? value : predicate()
  ) as Condition;
  const kind = Array.isArray(condition.all)
    ? "all"
    : Array.isArray(condition.any)
      ? "any"
      : condition.not
        ? "not"
        : "predicate";
  const children =
    kind === "not"
      ? [condition.not]
      : Array.isArray(condition[kind])
        ? (condition[kind] as unknown[])
        : [];
  return (
    <div className="condition-editor">
      <label className="field">
        Condition
        <select
          aria-label="Condition kind"
          value={kind}
          disabled={disabled}
          onChange={(e) =>
            onChange(
              e.target.value === "predicate"
                ? predicate()
                : e.target.value === "not"
                  ? { not: predicate() }
                  : { [e.target.value]: [predicate()] },
            )
          }
        >
          <option value="predicate">Registered fact</option>
          <option value="all">All conditions (AND)</option>
          <option value="any">Any condition (OR)</option>
          <option value="not">Negate (NOT)</option>
        </select>
      </label>
      {kind === "predicate" ? (
        <div className="toolbar">
          <label className="field">
            Fact
            <select
              value={String(condition.fact ?? "")}
              disabled={disabled}
              onChange={(e) =>
                onChange({
                  ...condition,
                  fact: e.target.value,
                  value: ["boolean", "bool"].includes(facts[e.target.value])
                    ? false
                    : "",
                })
              }
            >
              {Object.entries(facts).map(([key, type]) => (
                <option key={key} value={key}>
                  {key} · {type}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Operator
            <select
              value={String(condition.op ?? "eq")}
              disabled={disabled}
              onChange={(e) => onChange({ ...condition, op: e.target.value })}
            >
              {operators.map((op) => (
                <option key={op}>{op}</option>
              ))}
            </select>
          </label>
          <label className="field">
            {facts[String(condition.fact)] || "Typed"} value
            <TypedValue
              value={condition.value}
              type={facts[String(condition.fact)] || "string"}
              op={String(condition.op)}
              disabled={disabled}
              onChange={(v) => onChange({ ...condition, value: v })}
            />
          </label>
        </div>
      ) : (
        <div className="condition-children">
          {children.map((child, i) => (
            <div key={i}>
              <ConditionEditor
                value={child}
                facts={facts}
                operators={operators}
                disabled={disabled || depth >= 7}
                depth={depth + 1}
                onChange={(next) => {
                  if (kind === "not") onChange({ not: next });
                  else
                    onChange({
                      [kind]: children.map((c, j) => (j === i ? next : c)),
                    });
                }}
              />
              {kind !== "not" && children.length > 1 ? (
                <Button
                  size="sm"
                  disabled={disabled}
                  onClick={() =>
                    onChange({ [kind]: children.filter((_, j) => j !== i) })
                  }
                >
                  Remove condition
                </Button>
              ) : null}
            </div>
          ))}
          {kind !== "not" ? (
            <Button
              size="sm"
              disabled={disabled || children.length >= 20 || depth >= 7}
              onClick={() => onChange({ [kind]: [...children, predicate()] })}
            >
              Add condition
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}
