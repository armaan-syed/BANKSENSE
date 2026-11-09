import { useEffect, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";

export default function Chart({ data, layout, ariaLabel }) {
  const containerRef = useRef(null);
  const key = JSON.stringify({ data, layout });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return undefined;
    }
    Plotly.react(
      element,
      data,
      {
        autosize: true,
        margin: { l: 120, r: 20, t: 10, b: 40 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { family: "system-ui, sans-serif", color: "#334155" },
        ...layout,
      },
      { responsive: true, displayModeBar: false },
    );
    return () => Plotly.purge(element);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <div
      className="chart"
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
    />
  );
}
