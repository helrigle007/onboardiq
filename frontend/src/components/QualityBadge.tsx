interface QualityBadgeProps {
  score: number;
  showLabel?: boolean;
}

export function QualityBadge({ score, showLabel = false }: QualityBadgeProps) {
  const pct = Math.round(score * 100);

  let colorClasses: string;
  let label: string;

  if (score >= 0.8) {
    colorClasses = 'bg-green-100 text-green-700';
    label = 'Excellent';
  } else if (score >= 0.7) {
    colorClasses = 'bg-amber-100 text-amber-700';
    label = 'Good';
  } else {
    colorClasses = 'bg-red-100 text-red-700';
    label = 'Needs Work';
  }

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClasses}`}>
      {pct}%
      {showLabel && <span className="ml-0.5">{label}</span>}
    </span>
  );
}
