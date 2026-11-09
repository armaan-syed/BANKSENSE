import { useEffect, useMemo, useState } from "react";

import { getAnalytics, getComplaints } from "../api/client";
import { PRIORITY_ORDER } from "../constants";
import Chart from "./Chart";
import RecentComplaints from "./RecentComplaints";

const CHART_LAYOUT = {
  height: 280,
  xaxis: { gridcolor: "#e2e8f0", zeroline: false },
  yaxis: { gridcolor: "#e2e8f0", zeroline: false },
};

export default function AnalyticsDashboard({ refreshKey }) {
  const [analytics, setAnalytics] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([getAnalytics(), getComplaints(20, 0)])
      .then(([analyticsData, complaintsData]) => {
        if (!active) {
          return;
        }
        setAnalytics(analyticsData);
        setRecent(complaintsData.items);
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [refreshKey]);

  const priorityCounts = useMemo(() => {
    const counts = Object.fromEntries(PRIORITY_ORDER.map((name) => [name, 0]));
    for (const row of analytics?.by_priority ?? []) {
      counts[row.priority] = row.count;
    }
    return counts;
  }, [analytics]);

  const intentChart = useMemo(() => {
    const rows = (analytics?.by_intent ?? []).slice(0, 10).reverse();
    return [
      {
        type: "bar",
        orientation: "h",
        x: rows.map((row) => row.count),
        y: rows.map((row) => row.intent.replaceAll("_", " ")),
        marker: { color: "#2563eb" },
        hovertemplate: "%{y}: %{x}<extra></extra>",
      },
    ];
  }, [analytics]);

  const priorityChart = useMemo(
    () => [
      {
        type: "bar",
        x: PRIORITY_ORDER,
        y: PRIORITY_ORDER.map((name) => priorityCounts[name] ?? 0),
        marker: {
          color: ["#b91c1c", "#ea580c", "#ca8a04", "#0f766e"],
        },
        hovertemplate: "%{x}: %{y}<extra></extra>",
      },
    ],
    [priorityCounts],
  );

  if (loading) {
    return <p className="muted">Loading dashboard...</p>;
  }
  if (error) {
    return <p className="error-box">{error}</p>;
  }
  if (!analytics || analytics.total_complaints === 0) {
    return (
      <section className="card">
        <h2>Dashboard</h2>
        <p className="muted">
          No analysed complaints yet. Submit a message to populate the
          dashboard.
        </p>
      </section>
    );
  }

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <h2>Dashboard</h2>
          <p className="muted small">
            Counts come only from records stored by this prototype
            {analytics.includes_demo
              ? ", including clearly labelled demo records."
              : "."}
          </p>
        </div>
      </div>

      <div className="cards">
        <div className="stat-card">
          <span className="stat-label">Analysed complaints</span>
          <strong className="stat-value">{analytics.total_complaints}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Critical priority</span>
          <strong className="stat-value">{priorityCounts.critical ?? 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">High priority</span>
          <strong className="stat-value">{priorityCounts.high ?? 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Demo records</span>
          <strong className="stat-value">
            {analytics.includes_demo ? "Included" : "None"}
          </strong>
        </div>
      </div>

      <div className="chart-grid">
        <div className="card">
          <h3>Top intents</h3>
          <Chart
            data={intentChart}
            layout={CHART_LAYOUT}
            ariaLabel="Bar chart of the most common complaint intents"
          />
        </div>
        <div className="card">
          <h3>Priority breakdown</h3>
          <Chart
            data={priorityChart}
            layout={CHART_LAYOUT}
            ariaLabel="Bar chart of complaints by suggested priority"
          />
        </div>
      </div>

      <div className="card">
        <h3>Recent complaints</h3>
        <RecentComplaints items={recent} />
      </div>
    </section>
  );
}
