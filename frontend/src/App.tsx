import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Intro } from "@/components/Intro";
import { Shell } from "@/components/Shell";
import { INTRO_KEY, prefersReducedMotion } from "@/lib/config";
import { useAuth, Login } from "./auth";
import type { ReactNode } from "react";
const Overview = lazy(() => import("@/pages/Overview"));
const RequestStudio = lazy(() => import("@/pages/RequestStudio"));
const BuyerInbox = lazy(() => import("@/pages/BuyerInbox"));
const DecisionXray = lazy(() => import("@/pages/DecisionXray"));
const BatchLab = lazy(() => import("@/pages/BatchLab"));
const PolicyReactor = lazy(() => import("@/pages/PolicyReactor"));
const SupplierConstellation = lazy(
  () => import("@/pages/SupplierConstellation"),
);
const ContractVault = lazy(() => import("@/pages/ContractVault"));
const PurchaseOrders = lazy(() =>
  import("@/pages/Records").then((m) => ({ default: m.PurchaseOrders })),
);
const Sourcing = lazy(() =>
  import("@/pages/Records").then((m) => ({ default: m.Sourcing })),
);
const AuditTrail = lazy(() =>
  import("@/pages/Records").then((m) => ({ default: m.AuditTrail })),
);

export default function App() {
  const [intro, setIntro] = useState(
    () => !localStorage.getItem(INTRO_KEY) && !prefersReducedMotion(),
  );

  const finishIntro = useCallback(() => {
    localStorage.setItem(INTRO_KEY, "1");
    setIntro(false);
  }, []);

  useEffect(() => {
    const replay = () => setIntro(true);
    window.addEventListener("corvo:replay-intro", replay);
    return () => window.removeEventListener("corvo:replay-intro", replay);
  }, []);

  const { identity } = useAuth();
  if (!identity) return <Login />;
  return (
    <>
      {intro ? <Intro onDone={finishIntro} /> : null}
      <Suspense
        fallback={
          <div className="p-10" role="status">
            Loading workspace…
          </div>
        }
      >
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Overview />} />
            <Route path="request-studio" element={<RequestStudio />} />
            <Route
              path="inbox"
              element={
                <RoleGate>
                  <BuyerInbox />
                </RoleGate>
              }
            />
            <Route path="decision-xray" element={<DecisionXray />} />
            <Route path="decision-xray/:requestId" element={<DecisionXray />} />
            <Route path="batch-lab" element={<BatchLab />} />
            <Route
              path="policy-reactor"
              element={
                <RoleGate>
                  <PolicyReactor />
                </RoleGate>
              }
            />
            <Route path="suppliers" element={<SupplierConstellation />} />
            <Route path="contracts" element={<ContractVault />} />
            <Route path="contracts/:contractId" element={<ContractVault />} />
            <Route
              path="purchase-orders"
              element={
                <RoleGate>
                  <PurchaseOrders />
                </RoleGate>
              }
            />
            <Route
              path="sourcing"
              element={
                <RoleGate>
                  <Sourcing />
                </RoleGate>
              }
            />
            <Route
              path="audit"
              element={
                <RoleGate>
                  <AuditTrail />
                </RoleGate>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </>
  );
}

function RoleGate({ children }: { children: ReactNode }) {
  const { identity } = useAuth();
  return identity?.role === "requester" ? (
    <div className="p-10" role="alert">
      This workspace requires buyer or admin access.
    </div>
  ) : (
    children
  );
}
