import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api";
import { setToken } from "@/api/http";
import { Button, ErrorBlock } from "@/components/ui";
import { Wordmark } from "@/components/Monogram";
type Identity = { id: string; role: "admin" | "buyer" | "requester" };
type Auth = {
  identity: Identity | null;
  login: (body: {
    username?: string;
    role?: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
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
    const session = await api.login(body);
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
    <Context.Provider value={{ identity, login, logout }}>
      {children}
    </Context.Provider>
  );
}
export function Login() {
  const auth = useAuth();
  const [kind, setKind] = useState("role");
  const [role, setRole] = useState("requester");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const wait = Math.max(0, Math.ceil((until - now) / 1000));
  return (
    <main className="login-page grid-bg">
      <form
        className="surface-dark login-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
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
        <Wordmark className="text-[40px]" />
        <div className="eyebrow mt-6 text-lime">PROCUREMENT OPERATIONS</div>
        <h1 className="font-display mt-3 text-[32px]">Enter your workspace.</h1>
        <p className="mt-3 text-lavender">
          Sign in to work with live procurement data.
        </p>
        <label className="field mt-6">
          Account type
          <select
            aria-label="Account type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
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
              onChange={(e) => setRole(e.target.value)}
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
        <label className="field">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error ? <ErrorBlock error={error} /> : null}
        <Button
          type="submit"
          variant="lime"
          busy={busy}
          disabled={wait > 0}
          className="mt-5 w-full"
        >
          {wait ? `Try again in ${wait}s` : "Sign in"}
        </Button>
        <p className="mt-5 text-[12px] text-lavender">
          Your session stays in memory. Reloading requires sign-in.
        </p>
      </form>
    </main>
  );
}
