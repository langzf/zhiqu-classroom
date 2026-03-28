import { RouterProvider } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import { router } from './router';

function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div style={{ padding: 24, textAlign: 'center', marginTop: 80 }}>
      <h2 style={{ fontSize: 18, marginBottom: 12 }}>出了点问题</h2>
      <p style={{ color: '#6B7280', marginBottom: 16 }}>{error.message}</p>
      <button
        onClick={resetErrorBoundary}
        style={{
          padding: '8px 24px',
          background: 'var(--color-primary, #4F46E5)',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          fontSize: 14,
        }}
      >
        重试
      </button>
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
