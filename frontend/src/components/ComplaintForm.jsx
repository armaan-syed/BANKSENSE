import { useState } from "react";

import { analyzeComplaint } from "../api/client";
import { MAX_TEXT_LENGTH, MODELS } from "../constants";

export default function ComplaintForm({ onResult }) {
  const [text, setText] = useState("");
  const [model, setModel] = useState(MODELS[0].value);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const remaining = MAX_TEXT_LENGTH - text.length;
  const canSubmit = text.trim().length > 0 && remaining >= 0 && !pending;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      const result = await analyzeComplaint(text.trim(), model);
      onResult(result);
    } catch (requestError) {
      const field = requestError.field ? ` (${requestError.field})` : "";
      setError(`${requestError.message}${field}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="complaint-text">Customer message</label>
        <textarea
          id="complaint-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Paste the banking complaint or query here..."
          rows={6}
          disabled={pending}
        />
        <div className="form-meta">
          <span className={remaining < 0 ? "over-limit" : "muted"}>
            {text.length} / {MAX_TEXT_LENGTH} characters
          </span>
          {remaining < 0 && (
            <span className="error-text">Message is too long.</span>
          )}
        </div>
      </div>

      <div className="field">
        <label htmlFor="model-select">Classification model</label>
        <select
          id="model-select"
          value={model}
          onChange={(event) => setModel(event.target.value)}
          disabled={pending}
        >
          {MODELS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error-box">{error}</p>}

      <button type="submit" disabled={!canSubmit}>
        {pending ? "Analysing..." : "Analyse complaint"}
      </button>
      <p className="muted small">
        Results are decision support only. Confidence is model output, and
        priority is a rule suggestion, not a fraud or risk score.
      </p>
    </form>
  );
}
