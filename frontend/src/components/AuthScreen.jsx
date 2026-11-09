export default function AuthScreen({
  configured,
  loading,
  error,
  onSignIn,
}) {
  return (
    <div className="app auth-shell">
      <header className="auth-heading">
        <p className="eyebrow">NLP banking complaint triage</p>
        <h1>BankSense</h1>
        <p className="muted">
          Sign in with an invited Google account to analyse complaints and view
          your private dashboard.
        </p>
      </header>

      <section className="card auth-card">
        {!configured ? (
          <>
            <h2>Supabase is not configured</h2>
            <p className="muted">
              Add <code>VITE_SUPABASE_URL</code> and{" "}
              <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> to the root{" "}
              <code>.env</code> file, then restart the frontend.
            </p>
          </>
        ) : loading ? (
          <p className="muted">Checking your session…</p>
        ) : (
          <>
            <h2>Sign in</h2>
            <p className="muted">
              BankSense is invite-only. Use the Google account that was added to
              the Supabase project.
            </p>
            <button type="button" className="google-button" onClick={onSignIn}>
              Continue with Google
            </button>
          </>
        )}

        {error && <p className="error-box auth-error">{error}</p>}
      </section>
    </div>
  );
}
