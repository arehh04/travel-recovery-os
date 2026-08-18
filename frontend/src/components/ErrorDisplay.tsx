/** Error display component. */

interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ message, onRetry }: Props) {
  return (
    <div className="error-display" data-testid="error-display">
      <h3>Something went wrong</h3>
      <p>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          Try Again
        </button>
      )}
    </div>
  );
}
