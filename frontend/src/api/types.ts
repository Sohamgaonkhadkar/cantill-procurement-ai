import { z } from "zod";
export * from "./generated";
export const ROUTES = [
  "CONTRACT_PO",
  "EMERGENCY_PO",
  "SPOT_PO",
  "RFQ",
  "RFP",
  "CAPEX_SOURCING",
  "NEW_ITEM_SOURCING",
  "NOT_PROCESSED",
] as const;
export type Route = (typeof ROUTES)[number];
export type RequestStatus = "pending" | "approved" | "overridden";
export type Urgency = "Normal" | "Emergency";
export const RouteSchema = z.enum(ROUTES);
export const RunSummarySchema = z.object({
  id: z.string(),
  created_at: z.string(),
  input_hash: z.string(),
  data_hash: z.string(),
  policy_hash: z.string(),
  output_hash: z.string(),
  status: z.string(),
  counts: z.record(z.string(), z.number()),
  explicit_policy: z.string().nullable(),
  line_count: z.number(),
  requirement_count: z.number(),
  issue_count: z.number(),
});
export type RunSummary = z.infer<typeof RunSummarySchema>;
export const OverviewSchema = z.object({
  items: z.number(),
  suppliers: z.number(),
  contracts: z.number(),
  runs: z.number(),
  pending_requirements: z.number(),
  purchase_orders: z.number(),
  sourcing_requests: z.number(),
  latest_run: RunSummarySchema.nullable(),
});
export const MasterSchema = z.object({
  items: z.array(
    z
      .object({
        item_code: z.string(),
        description: z.string(),
        uom: z.string(),
        category: z.string(),
        item_type: z.string(),
        standard_price: z.string(),
      })
      .passthrough(),
  ),
  plants: z.array(
    z.object({ plant: z.string(), name: z.string() }).passthrough(),
  ),
  suppliers: z.array(
    z
      .object({
        supplier_id: z.string(),
        name: z.string(),
        status: z.string(),
        categories: z.string(),
        on_time_pct: z.string(),
        quality_rating: z.string(),
      })
      .passthrough(),
  ),
});
export const ContractSchema = z
  .object({
    contract_id: z.string(),
    supplier_id: z.string(),
    start_date: z.string(),
    end_date: z.string(),
    value_cap: z.string(),
    consumed_value: z.string(),
    lines: z.array(
      z
        .object({ item_code: z.string(), uom: z.string(), rate: z.string() })
        .passthrough(),
    ),
    baseline_consumed_value: z.string().optional(),
    committed_value: z.string().optional(),
    remaining_value: z.string().optional(),
    supplier_status: z.string().optional(),
    valid_as_of: z.boolean().optional(),
    provenance: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough();
export type Contract = z.infer<typeof ContractSchema>;
export const ProposalSchema = z
  .object({
    id: z.string(),
    status: z.string(),
    contract: ContractSchema.nullable(),
    source_text: z.string(),
    source_hash: z.string(),
    validation_error: z.string().nullable(),
    signature_verified: z.literal(false),
    manual_entry_required: z.boolean().optional(),
  })
  .passthrough();
export const AuditSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  actor: z.string(),
  action: z.string(),
  details: z.record(z.string(), z.unknown()),
});
export const RegistrySchema = z.object({
  facts: z.record(z.string(), z.string()),
  operators: z.array(z.string()),
  boolean_operators: z.array(z.string()),
  routes: z.array(z.string()),
  example: z.unknown(),
});
export function pageSchema<T extends z.ZodType>(schema: T) {
  return z
    .object({
      items: z.array(schema),
      total: z.number(),
      offset: z.number(),
      limit: z.number(),
    })
    .passthrough();
}
export type PageOf<T> = {
  items: T[];
  total: number;
  offset: number;
  limit: number;
};
