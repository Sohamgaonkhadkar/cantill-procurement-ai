import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api";
import { setToken } from "@/api/http";
import { Button, ErrorBlock } from "@/components/ui";
import { Wordmark } from "@/components/Monogram";
import { HERO_POSTER } from "@/components/media/assets";
type Identity = {
  id: string;
  role: "admin" | "buyer" | "requester";
  workspace_mode?: "live" | "demo";
};
type Auth = {
  identity: Identity | null;
  login: (body: {
    username?: string;
    role?: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  register: (body: {
    username: string;
    display_name: string;
    password: string;
  }) => Promise<void>;
};
const Context = createContext<Auth | null>(null);
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("Auth provider missing");
  return value;
}
export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const qc = useQueryClient();
  const clear = () => {
    setToken(null);
    setIdentity(null);
    qc.clear();
  };
  useEffect(() => {
    window.addEventListener("corvo:unauthorized", clear);
    return () => window.removeEventListener("corvo:unauthorized", clear);
  }, []);
  async function login(body: {
    username?: string;
    role?: string;
    password: string;
  }) {
    await acceptSession(await api.login(body));
  }
  async function register(body: {
    username: string;
    display_name: string;
    password: string;
  }) {
    await acceptSession(await api.register(body));
  }
  async function acceptSession(session: { access_token: string }) {
    setToken(session.access_token);
    try {
      const me = await api.me();
      qc.clear();
      setIdentity(me);
    } catch (e) {
      clear();
      throw e;
    }
  }
  async function logout() {
    await api.logout();
    clear();
  }
  return (
    <Context.Provider value={{ identity, login, logout, register }}>
      {children}
    </Context.Provider>
  );
}
export function Login() {
  const auth = useAuth();
  const [kind, setKind] = useState("role");
  const [role, setRole] = useState("requester");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [creating, setCreating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(Date.now());
  const options = useQuery({
    queryKey: ["auth-options"],
    queryFn: api.authOptions,
    retry: false,
  });
  const publicPassword =
    kind === "role"
      ? options.data?.roles.find((item) => item.role === role)?.password
      : undefined;
  useEffect(() => {
    if (options.data?.submission_access === false) {
      setKind("individual");
      setPassword("");
      setShowPassword(false);
    }
  }, [options.data?.submission_access]);
  useEffect(() => {
    if (publicPassword) {
      setPassword(publicPassword);
      setShowPassword(true);
    }
  }, [publicPassword]);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const wait = Math.max(0, Math.ceil((until - now) / 1000));
  return (
    <main className="login-page">
      <aside className="login-story" aria-label="About Corvo">
        <img
          className="login-story-image"
          src={HERO_POSTER.src}
          alt=""
          aria-hidden="true"
        />
        <div className="login-story-top">
          <Wordmark className="text-[28px]" />
          <span className="eyebrow">PROCUREMENT OPERATIONS</span>
        </div>
        <div className="login-story-copy">
          <span className="login-kicker">
            <span aria-hidden="true" /> BUILT FOR THE DECISION
          </span>
          <h2>
            Every request.
            <br />A reasoned <em>decision.</em>
          </h2>
          <p>
            Bring requests, suppliers and policy together. Move forward with the
            evidence in view.
          </p>
        </div>
        <div className="login-story-bottom">
          <div className="login-process">
            <span>01 / Request</span>
            <span>02 / Evaluate</span>
            <span>03 / Approve</span>
          </div>
          <p>Clarity at every stage. Control at every step.</p>
        </div>
      </aside>
      <div className="login-form-region">
        <form
          className="surface-dark login-card"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(null);
            try {
              if (creating && kind === "individual")
                await auth.register({
                  username,
                  display_name: displayName,
                  password,
                });
              else
                await auth.login(
                  kind === "role" ? { role, password } : { username, password },
                );
              setPassword("");
            } catch (e) {
              setError(e);
              if (e instanceof ApiError && e.retryAfter)
                setUntil(Date.now() + e.retryAfter * 1000);
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="login-form-brand">
            <Wordmark className="text-[32px]" />
          </div>
          <div className="eyebrow mt-6 text-lime">PROCUREMENT OPERATIONS</div>
          <h1 className="font-display mt-3 text-[32px]">
            {creating ? "Create your account." : "Enter your workspace."}
          </h1>
          <p className="mt-3 text-lavender">
            {options.data?.workspace_mode === "demo"
              ? "Explore the isolated demo with fictional procurement data."
              : "Sign in to work with live procurement data."}
          </p>
          {options.data?.workspace_mode === "demo" ? (
            <div className="demo-workspace-invite" role="note">
              <strong>Demo workspace · fictional data</strong>
              <p>
                Select a controlled role below. Its public demo password fills
                automatically. Changes stay in this separate workspace.
              </p>
              <a href="https://corvo-procurement.vercel.app">
                Return to the private live workspace ↗
              </a>
            </div>
          ) : options.data?.demo_url ? (
            <div className="demo-workspace-invite">
              <strong>Want automatic role passwords?</strong>
              <p>
                Try Admin, Buyer and Requester in a separate workspace with
                fictional data.
              </p>
              <a href={options.data.demo_url}>Open isolated demo workspace ↗</a>
            </div>
          ) : null}
          <label className="field mt-6">
            Account type
            <select
              aria-label="Account type"
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setCreating(false);
                setPassword("");
                setShowPassword(false);
                setError(null);
              }}
            >
              <option value="role">Controlled role account</option>
              <option value="individual">Individual account</option>
            </select>
          </label>
          {kind === "role" ? (
            <label className="field">
              Role
              <select
                aria-label="Role"
                value={role}
                onChange={(e) => {
                  setRole(e.target.value);
                  setPassword("");
                  setShowPassword(false);
                  setError(null);
                }}
              >
                <option value="requester">Requester</option>
                <option value="buyer">Buyer</option>
                <option value="admin">Admin</option>
              </select>
            </label>
          ) : (
            <label className="field">
              Username
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
          )}
          {kind === "individual" && options.data?.registration_enabled ? (
            <div className="mt-4 mb-4">
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  setCreating(!creating);
                  setError(null);
                  setPassword("");
                  setShowPassword(false);
                }}
              >
                {creating
                  ? "Already have an account? Sign in"
                  : "New here? Create account"}
              </Button>
              {creating ? (
                <p className="text-sm text-lavender mt-3">
                  Create a Requester account for your own procurement requests.
                </p>
              ) : null}
            </div>
          ) : null}
          {creating ? (
            <label className="field">
              Full name
              <input
                aria-label="Full name"
                required
                maxLength={100}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </label>
          ) : null}
          {creating ? (
            <p className="text-sm text-lavender mb-3">
              Username: 3–64 lowercase letters, digits, dots, underscores or
              hyphens; start with a letter. Password: at least 15 characters.
            </p>
          ) : null}
          {publicPassword ? (
            <p className="text-sm text-lavender mt-3 mb-3">
              {options.data?.workspace_mode === "demo"
                ? "Public demo password filled automatically for the selected role."
                : "Submission password is filled automatically for the selected shared role."}
            </p>
          ) : null}
          {!options.isPending && !options.data?.submission_access ? (
            <p className="text-sm text-lavender mb-3">
              {kind === "role"
                ? "Use the private password assigned to the selected role. Contact the workspace administrator for access."
                : options.data?.registration_enabled
                  ? "Already registered? Enter your username and password. New users can create a Requester account above."
                  : "Use your private individual credentials. Ask the workspace administrator for access."}
            </p>
          ) : null}
          <label className="field">
            Password
            <input
              type={showPassword ? "text" : "password"}
              autoComplete={creating ? "new-password" : "current-password"}
              required
              minLength={creating ? 15 : 1}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label className="mt-3 mb-3 flex items-center gap-2 text-sm text-lavender">
            <input
              type="checkbox"
              checked={showPassword}
              onChange={(e) => setShowPassword(e.target.checked)}
            />
            Show password
          </label>
          {options.error ? <ErrorBlock error={options.error} /> : null}
          {error ? <ErrorBlock error={error} /> : null}
          <Button
            type="submit"
            variant="lime"
            busy={busy}
            disabled={wait > 0}
            className="mt-5 w-full"
          >
            {wait
              ? `Try again in ${wait}s`
              : creating
                ? "Create account & sign in"
                : "Sign in"}
          </Button>
          <p className="mt-5 text-[12px] text-lavender">
            Your session stays in memory. Reloading requires sign-in.
          </p>
        </form>
        <div className="login-footer">
          <span className="login-secure-mark" aria-hidden="true">
            ↗
          </span>{" "}
          A private workspace for considered decisions.
        </div>
      </div>
    </main>
  );
}
