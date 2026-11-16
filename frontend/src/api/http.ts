import { z } from "zod";
import { API_BASE_URL } from "@/lib/config";
import {
  LoginResponseSchema,
  AuthOptionsSchema,
  DemoPreviewResponseSchema,
  RunResponseSchema,
  RequirementResponseSchema,
  PolicyResponseSchema,
  ComparisonResponseSchema,
  SimulationResponseSchema,
  ActionResponseSchema,
  ChatResponseSchema,
  AIStatusSchema,
  RankingSchema,
  ProcessingResultSchema,
} from "./generated";
import {
  AuditSchema,
  ContractSchema,
  MasterSchema,
  OverviewSchema,
  ProposalSchema,
  RegistrySchema,
  RunSummarySchema,
  pageSchema,
} from "./types";
import type { PolicyDefinition } from "./generated";
let token: string | null = null;
export function setToken(value: string | null) {
  token = value;
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details: unknown[] = [],
    public retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
async function response(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (token) headers.set("Authorization", "Bearer " + token);
  let res: Response;
  try {
    res = await fetch(API_BASE_URL + path, { ...init, headers });
  } catch {
    throw new ApiError(
      "Unable to reach the API. Check your connection and retry.",
      0,
    );
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = body.error;
    const failure = new ApiError(
      err?.message ?? `Request failed (${res.status})`,
      res.status,
      err?.details ?? [],
      Number(res.headers.get("Retry-After")) || null,
    );
    if (res.status === 401 && !path.endsWith("/auth/login")) {
      token = null;
      window.dispatchEvent(new Event("corvo:unauthorized"));
    }
    throw failure;
  }
  return res;
}
export async function call<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const body = await (await response(path, init)).json();
  const parsed = schema.safeParse(body);
  if (!parsed.success)
    throw new ApiError(
      "API contract mismatch: " +
        parsed.error.issues
          .map((x) => x.path.join(".") + ": " + x.message)
          .slice(0, 3)
          .join("; "),
      502,
    );
  return parsed.data;
}
const json = (body: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const form = (file: File, fields: Record<string, string> = {}): RequestInit => {
  const body = new FormData();
  body.append("file", file);
  for (const [k, v] of Object.entries(fields)) if (v) body.append(k, v);
  return { method: "POST", body };
};
export const qs = (values: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(values))
    if (v !== undefined && v !== "") p.set(k, String(v));
  return p.size ? "?" + p : "";
};
const id = encodeURIComponent;
export const api = {
  demoPreview: (file?: File) =>
    call(
      "/api/demo/preview",
      DemoPreviewResponseSchema,
      file ? form(file) : { method: "POST", body: new FormData() },
    ),
  demoInput: async () => (await response("/api/demo/input.csv")).blob(),
  demoExport: async (file?: File) =>
    (
      await response(
        "/api/demo/export.csv",
        file ? form(file) : { method: "POST", body: new FormData() },
      )
    ).blob(),
  authOptions: () => call("/api/auth/options", AuthOptionsSchema),
  register: (body: {
    username: string;
    display_name: string;
    password: string;
  }) => call("/api/auth/register", LoginResponseSchema, json(body)),
  login: (identity: { role?: string; username?: string; password: string }) =>
    call("/api/auth/login", LoginResponseSchema, json(identity)),
  me: () =>
    call(
      "/api/auth/me",
      z.object({
        id: z.string(),
        role: z.enum(["admin", "buyer", "requester"]),
        demo_mode: z.boolean(),
        workspace_mode: z.enum(["live", "demo"]).optional(),
      }),
    ),
  logout: () =>
    call("/api/auth/logout", z.object({ revoked: z.boolean() }), {
      method: "POST",
    }),
  overview: () => call("/api/overview", OverviewSchema),
  masters: () => call("/api/master-data", MasterSchema),
  runs: (offset = 0) =>
    call("/api/runs" + qs({ offset, limit: 25 }), pageSchema(RunSummarySchema)),
  run: (runId: string) => call("/api/runs/" + id(runId), RunResponseSchema),
  processBatch: (file: File, version = "") =>
    call(
      "/api/process-batch",
      RunResponseSchema,
      form(file, { policy_version: version }),
    ),
  replay: (runId: string) =>
    call(
      "/api/runs/" + id(runId) + "/replay",
      z.object({
        run_id: z.string(),
        matches: z.boolean(),
        output_hash: z.string(),
        result: ProcessingResultSchema,
      }),
      { method: "POST" },
    ),
  compare: (left: string, right: string) =>
    call(
      "/api/runs/" + id(left) + "/compare/" + id(right),
      ComparisonResponseSchema,
    ),
  exportRun: async (runId: string) =>
    (await response("/api/runs/" + id(runId) + "/export.csv")).blob(),
  requirements: (filters: Record<string, string | number | undefined> = {}) =>
    call(
      "/api/requirements" + qs({ limit: 25, ...filters }),
      pageSchema(RequirementResponseSchema),
    ),
  requirement: (reqId: string, runId: string) =>
    call(
      "/api/requirements/" + id(reqId) + qs({ run_id: runId }),
      RequirementResponseSchema,
    ),
  approve: (reqId: string, runId: string, reason: string) =>
    call(
      "/api/requirements/" + id(reqId) + "/approve" + qs({ run_id: runId }),
      ActionResponseSchema,
      json({ reason }),
    ),
  override: (reqId: string, runId: string, route: string, reason: string) =>
    call(
      "/api/requirements/" + id(reqId) + "/override" + qs({ run_id: runId }),
      ActionResponseSchema,
      json({ route, reason }),
    ),
  aiStatus: () => call("/api/ai/status", AIStatusSchema),
  chat: (
    message: string,
    session_id?: string,
    options: {
      request_id?: string;
      expected_revision?: number;
      action?: "message" | "confirm" | "cancel";
      demo_data_acknowledged?: boolean;
    } = {},
  ) =>
    call(
      "/api/chat/messages",
      ChatResponseSchema,
      json({ message, ...(session_id ? { session_id } : {}), ...options }),
    ),
  session: (sessionId: string) =>
    call(
      "/api/chat/sessions/" + id(sessionId),
      z.object({
        session_id: z.string(),
        actor: z.string(),
        state: z.record(z.string(), z.unknown()),
        messages: z.array(z.record(z.string(), z.unknown())),
      }),
    ),
  policies: () =>
    call("/api/policies", z.object({ items: z.array(PolicyResponseSchema) })),
  registry: () => call("/api/policy-schema", RegistrySchema),
  createPolicy: (
    policy: PolicyDefinition,
    base_version: string,
    source_text = "",
  ) =>
    call(
      "/api/policies",
      PolicyResponseSchema,
      json({ policy, base_version, source_text }),
    ),
  editPolicy: (
    policy: PolicyDefinition,
    base_version: string,
    source_text = "",
  ) =>
    call(
      "/api/policies/" + id(policy.version),
      PolicyResponseSchema,
      json({ policy, base_version, source_text }, "PUT"),
    ),
  previewPolicy: (policy: PolicyDefinition, base_version: string) =>
    call(
      "/api/policies/preview",
      z.object({
        valid: z.literal(true),
        diff: z.array(z.record(z.string(), z.unknown())),
        policy: z.unknown(),
        snapshot_hash: z.string(),
      }),
      json({ policy, base_version }),
    ),
  uploadAmendment: (file: File, fields: Record<string, string>) =>
    call(
      "/api/policies/upload-amendment",
      PolicyResponseSchema,
      form(file, fields),
    ),
  propose: (
    text: string,
    version: string,
    effective_date: string,
    base_version: string,
  ) =>
    call(
      "/api/policies/propose-amendment",
      PolicyResponseSchema,
      json({ text, version, effective_date, base_version }),
    ),
  policyAction: (
    version: string,
    action: "review" | "approve" | "activate" | "deactivate",
    reason: string,
    manual_verification = false,
  ) =>
    call(
      "/api/policies/" + id(version) + "/" + action,
      z.object({}).passthrough(),
      json(action === "review" ? { reason, manual_verification } : { reason }),
    ),
  simulate: (version: string, runId: string) =>
    call(
      "/api/policies/" + id(version) + "/simulate",
      SimulationResponseSchema,
      json({ run_id: runId }),
    ),
  suppliers: (
    as_of: string,
    item_code: string,
    offset = 0,
    policy_version = "",
  ) =>
    call(
      "/api/preferred-suppliers" +
        qs({ as_of, item_code, offset, limit: 50, policy_version }),
      pageSchema(
        RankingSchema.and(
          z.object({ item_code: z.string(), rank: z.number() }),
        ),
      ),
    ),
  exportSuppliers: async (as_of: string, policy_version = "") =>
    (
      await response(
        "/api/preferred-suppliers/export.csv" + qs({ as_of, policy_version }),
      )
    ).blob(),
  contracts: (offset = 0, as_of = "") =>
    call(
      "/api/contracts" + qs({ offset, limit: 12, as_of }),
      pageSchema(ContractSchema),
    ),
  proposals: () =>
    call(
      "/api/contracts/proposals",
      z.object({ items: z.array(ProposalSchema) }),
    ),
  contract: (contractId: string, as_of = "") =>
    call("/api/contracts/" + id(contractId) + qs({ as_of }), ContractSchema),
  uploadContract: (file: File) =>
    call("/api/contracts/upload", ProposalSchema, form(file)),
  approveContract: (proposalId: string, contract: unknown, reason: string) =>
    call(
      "/api/contracts/proposals/" + id(proposalId) + "/approve",
      ContractSchema,
      json({ contract, reason }),
    ),
  actions: (kind: "purchase-orders" | "sourcing", offset = 0) =>
    call(
      "/api/" + kind + qs({ offset, limit: 25 }),
      pageSchema(ActionResponseSchema),
    ),
  action: (kind: "purchase-orders" | "sourcing", actionId: string) =>
    call("/api/" + kind + "/" + id(actionId), ActionResponseSchema),
  audit: (offset = 0, action = "") =>
    call(
      "/api/audit" + qs({ offset, limit: 25, action }),
      pageSchema(AuditSchema),
    ),
};
