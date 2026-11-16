import { AnimatePresence, motion } from "motion/react";
import {
  Suspense,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Archive,
  Command,
  Handshake,
  Inbox,
  Layers,
  LayoutGrid,
  Menu,
  MessageSquarePlus,
  Orbit,
  Receipt,
  ScanLine,
  ScrollText,
  Search,
  Workflow,
  X,
  type LucideIcon,
} from "lucide-react";
import { usePolicies } from "@/api/hooks";
import { useAuth } from "@/auth";
import { ErrorBlock } from "./ui";
import { APP_NAME, IS_MOCK } from "@/lib/config";
import { cn } from "@/utils/cn";
import { Monogram, Wordmark } from "./Monogram";
import { EASE_OUT, Kbd } from "./ui";
import { useDialogFocus } from "./useDialogFocus";

/* ---------- Shared shell context ---------- */

type PlantCtx = { plant: string; setPlant: (p: string) => void };
const PlantContext = createContext<PlantCtx>({
  plant: "ALL",
  setPlant: () => {},
});
export const usePlant = () => useContext(PlantContext);

const MainScrollContext = createContext<RefObject<HTMLElement | null>>({
  current: null,
});
export const useMainScroll = () => useContext(MainScrollContext);

/* ---------- Navigation ---------- */

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  theme: string;
};

export const NAV: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutGrid, theme: "home" },
  {
    to: "/request-studio",
    label: "Request Studio",
    icon: MessageSquarePlus,
    theme: "request-studio",
  },
  { to: "/inbox", label: "Buyer Inbox", icon: Inbox, theme: "inbox" },
  {
    to: "/decision-xray",
    label: "Decision X-Ray",
    icon: ScanLine,
    theme: "decision-xray",
  },
  { to: "/batch-lab", label: "Batch Lab", icon: Layers, theme: "batch-lab" },
  {
    to: "/policy-reactor",
    label: "Policy Reactor",
    icon: Workflow,
    theme: "policy-reactor",
  },
  {
    to: "/suppliers",
    label: "Supplier Constellation",
    icon: Orbit,
    theme: "suppliers",
  },
  {
    to: "/contracts",
    label: "Contract Vault",
    icon: Archive,
    theme: "contracts",
  },
  {
    to: "/purchase-orders",
    label: "Purchase Orders",
    icon: Receipt,
    theme: "purchase-orders",
  },
  { to: "/sourcing", label: "Sourcing", icon: Handshake, theme: "sourcing" },
  { to: "/audit", label: "Audit Trail", icon: ScrollText, theme: "audit" },
];

/* ---------- Rail ---------- */

function Rail() {
  const { identity } = useAuth();
  const nav = visibleNav(identity?.role);
  const groups = [
    {
      label: "Workspace",
      paths: ["/", "/request-studio", "/inbox", "/batch-lab"],
    },
    { label: "Intelligence", paths: ["/decision-xray", "/suppliers"] },
    { label: "Governance", paths: ["/policy-reactor"] },
    {
      label: "Records",
      paths: ["/contracts", "/purchase-orders", "/sourcing", "/audit"],
    },
  ];
  return (
    <nav aria-label="Primary" className="workspace-rail hidden lg:flex">
      <div className="rail-brand">
        <Monogram size={34} glow={false} />
        <Wordmark className="text-[25px]" />
      </div>
      <p className="rail-caption">Procurement operations</p>
      <div className="rail-links scroll-thin">
        {groups.map((group) => {
          const items = nav.filter((n) => group.paths.includes(n.to));
          return items.length ? (
            <section key={group.label}>
              <h2>{group.label}</h2>
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    aria-label={item.label}
                    className={({ isActive }) =>
                      cn("rail-link", isActive && "active")
                    }
                  >
                    <Icon size={17} aria-hidden />
                    {item.to === "/suppliers"
                      ? "Supplier Intelligence"
                      : item.label}
                  </NavLink>
                );
              })}
            </section>
          ) : null;
        })}
      </div>
      <div className="rail-account">
        <span>{identity?.id}</span>
        <small>
          {identity?.role} ·{" "}
          {identity?.workspace_mode === "demo"
            ? "fictional demo"
            : "live workspace"}
        </small>
      </div>
    </nav>
  );
}

/* ---------- Header ---------- */

function Header({
  onOpenPalette,
  onOpenMenu,
}: {
  onOpenPalette: () => void;
  onOpenMenu: () => void;
}) {
  const location = useLocation();
  const { identity, logout } = useAuth();
  const policies = usePolicies();
  const activePolicy = policies.data?.items
    .filter(
      (p) =>
        p.status === "active" &&
        p.effective_date <=
          new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
    )
    .sort((a, b) => b.effective_date.localeCompare(a.effective_date))[0];
  const [logoutError, setLogoutError] = useState<unknown>(null);
  const [profile, setProfile] = useState(false);
  const current =
    NAV.find((n) =>
      n.to === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(n.to),
    ) ?? NAV[0];

  return (
    <header className="workspace-header pointer-events-none fixed inset-x-0 top-0 z-40 flex h-[68px] items-center justify-between gap-4 px-4 lg:left-[244px] md:px-6">
      <div className="pointer-events-auto flex min-w-0 items-center gap-3">
        <button
          onClick={onOpenMenu}
          className="flex h-9 w-9 items-center justify-center text-lavender hover:text-porcelain lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <nav
          aria-label="Breadcrumb"
          className="flex min-w-0 items-center gap-2 text-[12px]"
        >
          <span className="eyebrow text-lavender/70">corvo / workspace</span>
          <span className="text-lavender/40">/</span>
          <span className="truncate font-medium text-porcelain">
            {current.label}
          </span>
        </nav>
        <span
          className={cn(
            "num hidden items-center gap-2 px-2 py-[3px] text-[10px] tracking-[0.12em] lg:flex",
            IS_MOCK ? "text-lime" : "text-mint",
          )}
          style={{
            clipPath:
              "polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,6px 100%,0 calc(100% - 6px))",
            background: IS_MOCK
              ? "rgba(215,255,63,0.1)"
              : "rgba(50,230,210,0.1)",
          }}
        >
          <span
            className="live-dot h-1.5 w-1.5 rounded-full bg-current"
            aria-hidden
          />
          {identity?.workspace_mode === "demo"
            ? "DEMO · FICTIONAL DATA"
            : IS_MOCK
              ? "MOCK · SYNTHETIC DATA"
              : "LIVE · API"}
        </span>
      </div>

      <div className="pointer-events-auto flex items-center gap-2">
        {activePolicy ? (
          <span className="num hidden items-center gap-2 text-[11px] tracking-[0.1em] text-lavender xl:flex">
            POLICY{" "}
            <span className="text-porcelain">{activePolicy.version}</span>
            <span className="text-lavender/40">· {activePolicy.status}</span>
          </span>
        ) : null}

        <button
          onClick={onOpenPalette}
          className="group flex h-9 items-center gap-2 bg-white/[0.05] px-3 text-[12px] text-lavender ring-1 ring-inset ring-lavender/20 hover:text-porcelain"
          aria-label="Open command palette"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden md:inline">Command</span>
          <span className="hidden items-center gap-0.5 md:flex">
            <Kbd>
              <Command className="inline h-2.5 w-2.5" />
            </Kbd>
            <Kbd>K</Kbd>
          </span>
        </button>
        <div className="relative">
          <button
            onClick={() => setProfile((p) => !p)}
            className="num flex h-9 w-9 items-center justify-center bg-ultra text-[11px] text-white hover:bg-ultra-hi"
            aria-expanded={profile}
            aria-label="Profile"
          >
            {identity?.id.slice(0, 2).toUpperCase()}
          </button>
          <AnimatePresence>
            {profile ? (
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18, ease: EASE_OUT }}
                className="surface-dark absolute right-0 top-11 w-64 p-4"
              >
                <div className="eyebrow text-lavender">Operator</div>
                <div className="mt-1 text-[14px]">{identity?.id}</div>
                <div className="num mt-1 text-[11px] text-lavender">
                  {identity?.role}
                </div>
                <button
                  className="mt-3 w-full bg-lime p-2 text-white"
                  onClick={async () => {
                    try {
                      await logout();
                    } catch (e) {
                      setLogoutError(e);
                    }
                  }}
                >
                  Sign out
                </button>
                {logoutError ? <ErrorBlock error={logoutError} /> : null}
                <div className="my-3 h-px bg-lavender/15" />
                <div className="num text-[11px] text-lavender">
                  DATA MODE ·{" "}
                  {identity?.workspace_mode === "demo"
                    ? "DEMO (fictional)"
                    : IS_MOCK
                      ? "MOCK (synthetic)"
                      : "LIVE (FastAPI)"}
                </div>
                <button
                  onClick={() => {
                    setProfile(false);
                    window.dispatchEvent(new Event("corvo:replay-intro"));
                  }}
                  className="mt-3 w-full bg-white/[0.06] py-2 text-[12px] hover:bg-white/10"
                >
                  Replay brand intro
                </button>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}

/* ---------- Command palette ---------- */

function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { identity } = useAuth();
  const dialog = useDialogFocus(open, onClose);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const navigate = useNavigate();
  const commands = useMemo(
    () =>
      [
        ...visibleNav(identity?.role).map((n) => ({
          id: n.to,
          label: `Open ${n.label}`,
          hint: n.to,
          run: () => navigate(n.to),
        })),
        {
          id: "new-request",
          label: "New purchase request",
          hint: "Request Studio",
          run: () => navigate("/request-studio"),
        },
        {
          id: "process-batch",
          label: "Process a CSV batch",
          hint: "Batch Lab",
          run: () => navigate("/batch-lab"),
        },
        {
          id: "simulate",
          label: "Simulate policy impact",
          hint: "Policy Reactor",
          run: () => navigate("/policy-reactor"),
        },
        {
          id: "xray",
          label: "Open latest Decision X-Ray",
          hint: "Decision X-Ray",
          run: () => navigate("/decision-xray"),
        },
        {
          id: "intro",
          label: "Replay brand intro",
          hint: "Brand",
          run: () => window.dispatchEvent(new Event("corvo:replay-intro")),
        },
      ].filter(
        (command) =>
          identity?.role !== "requester" || command.id !== "simulate",
      ),
    [navigate, identity?.role],
  );
  const list = commands.filter((c) =>
    c.label.toLowerCase().includes(q.trim().toLowerCase()),
  );

  useEffect(() => {
    if (open) {
      setQ("");
      setIdx(0);
    }
  }, [open]);

  const run = (i: number) => {
    const cmd = list[i];
    if (!cmd) return;
    onClose();
    cmd.run();
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[120] flex items-start justify-center bg-midnight/70 px-4 pt-[14vh] backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={onClose}
        >
          <motion.div
            role="dialog"
            ref={dialog}
            aria-modal="true"
            aria-label="Command palette"
            className="surface-dark w-full max-w-xl overflow-hidden"
            initial={{ y: -12, scale: 0.98, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -8, opacity: 0 }}
            transition={{ duration: 0.22, ease: EASE_OUT }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-lavender/15 px-4">
              <Search className="h-4 w-4 text-lime" />
              <input
                autoFocus
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setIdx(0);
                }}
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setIdx((i) => Math.min(list.length - 1, i + 1));
                  } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setIdx((i) => Math.max(0, i - 1));
                  } else if (e.key === "Enter") {
                    run(idx);
                  } else if (e.key === "Escape") {
                    onClose();
                  }
                }}
                placeholder="Jump to a screen or run an action…"
                className="h-14 w-full bg-transparent text-[15px] text-porcelain outline-none placeholder:text-lavender/60"
                aria-label="Search commands"
              />
              <Kbd>ESC</Kbd>
            </div>
            <ul
              className="scroll-thin max-h-[52vh] overflow-y-auto py-2"
              role="listbox"
            >
              {list.map((c, i) => (
                <li key={c.id} role="option" aria-selected={i === idx}>
                  <button
                    onMouseEnter={() => setIdx(i)}
                    onClick={() => run(i)}
                    className={cn(
                      "flex w-full items-center justify-between px-4 py-3 text-left text-[14px]",
                      i === idx ? "bg-ultra text-white" : "text-porcelain",
                    )}
                  >
                    <span>{c.label}</span>
                    <span
                      className={cn(
                        "num text-[11px]",
                        i === idx ? "text-white" : "text-lavender",
                      )}
                    >
                      {c.hint}
                    </span>
                  </button>
                </li>
              ))}
              {list.length === 0 ? (
                <li className="px-4 py-6 text-[13px] text-lavender">
                  No command matches “{q}”.
                </li>
              ) : null}
            </ul>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

/* ---------- Mobile navigation ---------- */

function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { identity } = useAuth();
  const dialog = useDialogFocus(open, onClose);
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          role="dialog"
          ref={dialog}
          aria-modal="true"
          aria-label="Mobile navigation"
          className="fixed inset-0 z-[110] flex flex-col overflow-y-auto bg-midnight/97 p-6 lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5, ease: EASE_OUT }}
        >
          <div className="flex items-center justify-between">
            <Wordmark className="text-[26px]" />
            <button
              onClick={onClose}
              className="flex h-10 w-10 items-center justify-center text-lavender"
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="mt-8 flex flex-col">
            {visibleNav(identity?.role).map((n, i) => (
              <motion.div
                key={n.to}
                initial={{ opacity: 0, x: -14 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.06 + i * 0.03,
                  duration: 0.35,
                  ease: EASE_OUT,
                }}
              >
                <NavLink
                  aria-label={n.label}
                  to={n.to}
                  end={n.to === "/"}
                  onClick={onClose}
                  className="flex items-baseline justify-between border-b border-lavender/10 py-3 font-display text-[26px] tracking-[-0.02em] text-porcelain"
                >
                  {n.label}
                  <span className="num text-[10px] text-lavender">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </NavLink>
              </motion.div>
            ))}
          </nav>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

/* ---------- Layout ---------- */

export function Shell() {
  const { identity } = useAuth();
  const location = useLocation();
  const themeKey =
    NAV.find((n) =>
      n.to === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(n.to),
    )?.theme ?? "home";
  const [plant, setPlant] = useState("ALL");
  const [palette, setPalette] = useState(false);
  const [menu, setMenu] = useState(false);
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setMenu(false);
    mainRef.current?.scrollTo({ top: 0 });
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const plantValue = useMemo(() => ({ plant, setPlant }), [plant]);

  return (
    <PlantContext.Provider value={plantValue}>
      <MainScrollContext.Provider value={mainRef}>
        <div className="relative h-full w-full overflow-hidden bg-midnight">
          <Rail />
          <Header
            onOpenPalette={() => setPalette(true)}
            onOpenMenu={() => setMenu(true)}
          />

          <main
            ref={mainRef}
            id="main"
            className="scroll-thin absolute inset-0 z-10 overflow-y-auto pt-[68px] lg:pl-[244px]"
          >
            {identity?.workspace_mode === "demo" ? (
              <div className="demo-workspace-banner" role="status">
                <strong>Isolated demo</strong>
                <span>
                  Fictional data · Changes do not affect the live workspace.
                </span>
                <a href="https://corvo-procurement.vercel.app">
                  Open live workspace ↗
                </a>
              </div>
            ) : null}
            <div key={themeKey} className="min-h-full">
              <Suspense
                fallback={
                  <div className="p-10" role="status">
                    Loading workspace…
                  </div>
                }
              >
                <Outlet />
              </Suspense>
            </div>
          </main>

          <MobileMenu open={menu} onClose={() => setMenu(false)} />
          <CommandPalette open={palette} onClose={() => setPalette(false)} />
          <span className="sr-only">{APP_NAME}</span>
        </div>
      </MainScrollContext.Provider>
    </PlantContext.Provider>
  );
}

function visibleNav(role?: string) {
  return NAV.filter(
    (n) =>
      role !== "requester" ||
      ![
        "/inbox",
        "/policy-reactor",
        "/purchase-orders",
        "/sourcing",
        "/audit",
      ].includes(n.to),
  );
}
