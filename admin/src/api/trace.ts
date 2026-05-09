const TRACE_PLATFORM_URL = import.meta.env.VITE_TRACE_PLATFORM_URL || 'https://trace.yueying.cloud';
const TRACE_PROJECT_KEY = import.meta.env.VITE_TRACE_PROJECT_KEY || 'zhiqu-classroom';
const TRACE_SERVICE_NAME = import.meta.env.VITE_TRACE_SERVICE_NAME || 'zhiqu-admin-web';
const TRACE_ENABLED = import.meta.env.VITE_TRACE_ENABLED !== '0';

export interface TraceContext {
  traceId: string;
  spanId: string;
  parentSpanId: string | null;
}

interface TraceLogOptions {
  traceContext?: TraceContext;
  path?: string;
  method?: string;
  statusCode?: number;
  durationMs?: number;
  error?: unknown;
  meta?: Record<string, unknown>;
}

function randomHex(bytes: number): string {
  const values = new Uint8Array(bytes);
  crypto.getRandomValues(values);
  return Array.from(values)
    .map((item) => item.toString(16).padStart(2, '0'))
    .join('');
}

export function createTraceContext(parentSpanId: string | null = null): TraceContext {
  return {
    traceId: `tr_${randomHex(12)}`,
    spanId: `sp_${randomHex(8)}`,
    parentSpanId,
  };
}

export function childSpan(traceContext: TraceContext): TraceContext {
  return {
    traceId: traceContext.traceId,
    spanId: `sp_${randomHex(8)}`,
    parentSpanId: traceContext.spanId,
  };
}

export function applyTraceHeaders(headers: Record<string, unknown>, traceContext: TraceContext): void {
  headers['x-trace-id'] = traceContext.traceId;
  headers['x-parent-span-id'] = traceContext.spanId;
  headers['x-client-app'] = TRACE_SERVICE_NAME;
}

export function reportTraceLog(level: string, message: string, options: TraceLogOptions = {}): void {
  if (!TRACE_ENABLED || !TRACE_PLATFORM_URL) {
    return;
  }

  const context = options.traceContext || createTraceContext();
  const payload = {
    source: 'frontend',
    logs: [
      {
        level,
        message,
        traceId: context.traceId,
        spanId: context.spanId,
        parentSpanId: context.parentSpanId,
        source: 'frontend',
        service: TRACE_SERVICE_NAME,
        path: options.path || window.location.pathname,
        method: options.method,
        statusCode: options.statusCode,
        timestamp: new Date().toISOString(),
        error: toErrorPayload(options.error),
        meta: {
          projectKey: TRACE_PROJECT_KEY,
          durationMs: options.durationMs,
          ...(options.meta || {}),
        },
      },
    ],
  };

  fetch(`${TRACE_PLATFORM_URL.replace(/\/$/, '')}/v1/logs/batch`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-client-app': TRACE_SERVICE_NAME },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {
    // Trace upload must never interrupt the admin app.
  });
}

function toErrorPayload(error: unknown): { name: string; message: string; stack: string } | undefined {
  if (!error) {
    return undefined;
  }
  if (error instanceof Error) {
    return {
      name: error.name || 'Error',
      message: error.message,
      stack: error.stack || '',
    };
  }
  return {
    name: 'Error',
    message: String(error),
    stack: '',
  };
}

let globalHandlersInstalled = false;

export function installGlobalTraceHandlers(): void {
  if (globalHandlersInstalled || !TRACE_ENABLED) {
    return;
  }
  globalHandlersInstalled = true;

  window.addEventListener('error', (event) => {
    reportTraceLog('error', 'window.error', {
      error: event.error,
      meta: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      },
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    reportTraceLog('error', 'window.unhandledrejection', {
      error: event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
    });
  });
}
