import React from "react";

/** A stale/missing analytics chunk must not break the operational application. */
export class ChartBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="notice warning" role="status">
        <div>
          <p>
            No se pudo cargar el gráfico. Los recuentos por fuente siguen
            disponibles debajo.
          </p>
          <button
            className="button small"
            onClick={() => window.location.reload()}
          >
            Recargar esta vista
          </button>
        </div>
      </div>
    ) : (
      this.props.children
    );
  }
}
