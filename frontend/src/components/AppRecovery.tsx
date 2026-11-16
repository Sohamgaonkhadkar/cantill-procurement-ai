import { Component, useEffect, type ReactNode } from "react";

export class AppRecovery extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            padding: 24,
            background: "#080b1f",
            color: "#f5f3ec",
          }}
          role="alert"
        >
          <section style={{ maxWidth: 440 }}>
            <h1>Let’s reload your workspace.</h1>
            <p>
              The application could not finish loading. Reload to get the latest
              version. Your saved procurement data is safe.
            </p>
            <a
              style={{
                display: "inline-block",
                padding: "12px 20px",
                background: "#d7ff3f",
                color: "#080b1f",
                marginTop: 16,
              }}
              href={window.location.pathname + "?reload=" + Date.now()}
            >
              Reload workspace
            </a>
          </section>
        </main>
      );
    return this.props.children;
  }
}

export function AppReady() {
  useEffect(() => {
    const boot = (window as Window & { corvoBoot?: { ready: boolean } })
      .corvoBoot;
    if (boot) boot.ready = true;
  }, []);
  return null;
}
