export default function SourceCard({ source }) {
  const relevance = Math.round(source.score * 100);

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noreferrer"
      className="source-card"
      title={`Relevance: ${relevance}%`}
    >
      <span className="source-ref">{source.reference}</span>
      <span className="source-score">{relevance}%</span>
    </a>
  );
}
