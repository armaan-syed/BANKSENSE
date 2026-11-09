import { PRIORITY_ORDER } from "../constants";

function PriorityBadge({ priority }) {
  const index = PRIORITY_ORDER.indexOf(priority);
  const tone = index === -1 ? "low" : priority;
  return <span className={`badge priority-${tone}`}>{priority}</span>;
}

export default function ResultView({ result }) {
  const created = new Date(result.created_at);
  const createdAt = Number.isNaN(created.getTime())
    ? result.created_at
    : created.toLocaleString();

  return (
    <section className="card result" aria-live="polite">
      <header className="result-header">
        <div>
          <p className="eyebrow">Complaint #{result.complaint_id}</p>
          <h2>{result.intent.replaceAll("_", " ")}</h2>
        </div>
        <PriorityBadge priority={result.priority} />
      </header>

      <dl className="facts">
        <div>
          <dt>Model confidence</dt>
          <dd>{(result.confidence * 100).toFixed(1)}%</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{result.model}</dd>
        </div>
        <div>
          <dt>Priority (rule suggestion)</dt>
          <dd className="capitalize">{result.priority}</dd>
        </div>
        <div>
          <dt>Recorded</dt>
          <dd>{createdAt}</dd>
        </div>
      </dl>

      <div className="panel">
        <h3>Why this priority</h3>
        <p>{result.priority_reason}</p>
        <p className="muted small">
          This is a configurable rule suggestion, not a validated fraud or risk
          score.
        </p>
      </div>

      <div className="panel">
        <h3>Summary</h3>
        {result.summary ? (
          <p>{result.summary}</p>
        ) : (
          <p className="muted">
            Summarisation is unavailable for this run. Other results are
            unaffected.
          </p>
        )}
      </div>

      <div className="panel">
        <div className="panel-heading">
          <h3>Similar stored cases</h3>
          <span className="muted small">
            Ranked by Sentence-BERT cosine similarity
          </span>
        </div>
        {result.similar_cases.length === 0 ? (
          <p className="muted">
            No similar stored cases yet. This is the first matching record.
          </p>
        ) : (
          <ul className="similar-list">
            {result.similar_cases.map((item) => (
              <li key={item.complaint_id}>
                <div className="similar-meta">
                  <span className="muted small">
                    Case #{item.complaint_id} ·{" "}
                    {(item.similarity * 100).toFixed(1)}% similar
                  </span>
                  <span className={`tag tag-${item.source}`}>
                    {item.source === "demo" ? "demo data" : "submitted"}
                  </span>
                </div>
                <p>{item.text}</p>
                <p className="muted small">
                  Predicted intent: {item.intent.replaceAll("_", " ")}
                </p>
              </li>
            ))}
          </ul>
        )}
        <p className="muted small">
          BANKING77 and seeded examples are benchmark/demo data, not verified
          bank case history.
        </p>
      </div>
    </section>
  );
}
