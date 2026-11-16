import type { Route } from "@/api";
// Format the backend's decimal text without converting money to IEEE-754.
export function formatNumber(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const raw = String(value);
  if (!/^-?\d+(?:\.\d+)?$/.test(raw)) return raw;
  const [integer, fraction] = raw.split(".");
  const sign = integer.startsWith("-") ? "-" : "";
  const digits = integer.replace("-", "");
  const tail = digits.slice(-3);
  const head = digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return (
    sign +
    (head ? head + "," : "") +
    tail +
    (fraction !== undefined ? "." + fraction : "")
  );
}
export function formatMoney(
  value: string | null | undefined,
  currency = "INR",
) {
  return value === null || value === undefined || value === ""
    ? "—"
    : (currency === "INR" ? "₹" : currency + " ") + formatNumber(value);
}
export const formatUnitPrice = formatMoney;
export const pad = (n: number, width = 3) => String(n).padStart(width, "0");
export function formatDate(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "—";
}
export function formatDateTime(value: string) {
  return value.replace("T", " ");
}
export const ROUTE_DESCRIPTION: Record<string, string> = {
  CONTRACT_PO: "Contract-backed purchase order recommendation",
  EMERGENCY_PO: "Emergency purchase order recommendation",
  SPOT_PO: "Spot purchase order recommendation",
  RFQ: "Request for quotation",
  RFP: "Request for proposal",
  CAPEX_SOURCING: "Capital sourcing",
  NEW_ITEM_SOURCING: "New item sourcing",
  NOT_PROCESSED: "Validation requires attention",
};
export const routeIsDirect = (r: Route) =>
  ["CONTRACT_PO", "SPOT_PO", "EMERGENCY_PO"].includes(r);
export const routeIsSourcing = (r: Route) =>
  ["RFQ", "RFP", "CAPEX_SOURCING", "NEW_ITEM_SOURCING"].includes(r);
