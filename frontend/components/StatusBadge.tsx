interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const label = status.replaceAll('_', ' ');
  return <span className={`status status-${status.toLowerCase()}`}>{label}</span>;
}
