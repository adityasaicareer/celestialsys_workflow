interface LoadingProps {
  label?: string;
  inline?: boolean;
}

export default function Loading({ label = 'Loading', inline = false }: LoadingProps) {
  return (
    <div className={inline ? 'loading-inline' : 'loading-page'} role="status" aria-label={label}>
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}
