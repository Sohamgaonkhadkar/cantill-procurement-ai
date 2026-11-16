import { StrictMode } from "react";
import { MotionConfig } from "motion/react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./auth";
import { AppRecovery, AppReady } from "./components/AppRecovery";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 15_000 },
    mutations: { retry: 0 },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppRecovery>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <MotionConfig reducedMotion="user">
              <App />
              <AppReady />
            </MotionConfig>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </AppRecovery>
  </StrictMode>,
);
