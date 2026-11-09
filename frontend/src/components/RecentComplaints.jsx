export default function RecentComplaints({ items, loading, error }) {
  if (loading) {
    return <p className="muted">Loading recent complaints...</p>;
  }
  if (error) {
    return <p className="error-box">{error}</p>;
  }
  if (!items.length) {
    return <p className="muted">No complaints have been analysed yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Message</th>
            <th>Intent</th>
            <th>Priority</th>
            <th>Source</th>
            <th>Recorded</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.complaint_id}>
              <td>{item.complaint_id}</td>
              <td className="message-cell" title={item.text}>
                {item.text}
              </td>
              <td>{item.intent.replaceAll("_", " ")}</td>
              <td className="capitalize">{item.priority}</td>
              <td>
                <span className={`tag tag-${item.source}`}>{item.source}</span>
              </td>
              <td>{item.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
