import { useEffect, useState } from "react";

import { getHealth } from "./api/client";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import ComplaintForm from "./components/ComplaintForm";
import ResultView from "./components/ResultView";

export default function App() {
  const [view, setView] = useState("analyze");
  const [result, setResult] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "error", database: "error", models: {} }));
  }, []);

  function handleResult(analysis) {
    setResult(analysis);
    setRefreshKey((key) => key + 1);
    getHealth().then(setHealth).catch(() => undefined);
  }

  const modelsReady = health?.models?.tfidf;
  const databaseOk = health?.database === "ok";

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <p className="eyebrow">NLP banking complaint triage</p>
          <h1>BankSense</h1>
          <p className="muted">
            Predict complaint intent, suggest a rule-based priority, and find
            semantically similar stored cases.
          </p>
        </div>
        <nav className="tabs" aria-label="Views">
          <button
            type="button"
            className={view === "analyze" ? "active" : ""}
            onClick={() => setView("analyze")}
          >
            Analyse
          </button>
          <button
            type="button"
            className={view === "dashboard" ? "active" : ""}
            onClick={() => setView("dashboard")}
          >
            Dashboard
          </button>
        </nav>
      </header>

      {!databaseOk && (
        <p className="error-box">
          The database is not available. Check the backend logs and
          <code> /api/health</code>.
        </p>
      )}
      {health && databaseOk && !modelsReady && (
        <p className="notice-box">
          NLP models are not loaded yet. Analysis will return a clear
          unavailable error until model artifacts are trained and placed in
          <code> backend/models/</code>.
        </p>
      )}

      {view === "analyze" ? (
        <main className="analyze-grid">
          <ComplaintForm onResult={handleResult} />
          {result ? (
            <ResultView result={result} />
          ) : (
            <section className="card placeholder">
              <h2>Result</h2>
              <p className="muted">
                Submit a banking complaint to see the predicted intent, model
                confidence, suggested priority, and similar stored cases.
              </p>
            </section>
          )}
        </main>
      ) : (
        <main>
          <AnalyticsDashboard refreshKey={refreshKey} />
        </main>
      )}

      <footer className="app-footer">
        <p className="muted small">
          BankSense is a decision-support prototype. It is not connected to any
          banking, payment, or customer-identity system, and it does not process
          real bank complaint volumes.
        </p>
      </footer>
    </div>
  );
}
