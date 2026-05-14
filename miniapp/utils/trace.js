const {
  TRACE_ENABLED,
  TRACE_PLATFORM_URL,
  TRACE_PROJECT_KEY,
  TRACE_SERVICE_NAME
} = require('./config');

function randomHex(length) {
  let value = '';
  for (let i = 0; i < length; i += 1) {
    value += Math.floor(Math.random() * 16).toString(16);
  }
  return value;
}

function createTraceContext(parentSpanId) {
  return {
    traceId: `tr_${randomHex(24)}`,
    spanId: `sp_${randomHex(16)}`,
    parentSpanId: parentSpanId || null
  };
}

function childSpan(traceContext) {
  return {
    traceId: traceContext.traceId,
    spanId: `sp_${randomHex(16)}`,
    parentSpanId: traceContext.spanId
  };
}

function applyTraceHeaders(header, traceContext) {
  header['x-trace-id'] = traceContext.traceId;
  header['x-parent-span-id'] = traceContext.spanId;
  header['x-client-app'] = TRACE_SERVICE_NAME;
}

function reportTraceLog(level, message, options) {
  if (!TRACE_ENABLED || !TRACE_PLATFORM_URL) return;

  const opts = options || {};
  const context = opts.traceContext || createTraceContext();
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
        path: opts.path || '',
        method: opts.method,
        statusCode: opts.statusCode,
        timestamp: new Date().toISOString(),
        error: toErrorPayload(opts.error),
        meta: Object.assign({
          projectKey: TRACE_PROJECT_KEY,
          durationMs: opts.durationMs,
          platform: 'wechat-miniapp',
          sdkVersion: getSdkVersion()
        }, opts.meta || {})
      }
    ]
  };

  wx.request({
    url: `${TRACE_PLATFORM_URL.replace(/\/$/, '')}/v1/logs/batch`,
    method: 'POST',
    data: payload,
    header: {
      'content-type': 'application/json',
      'x-client-app': TRACE_SERVICE_NAME
    },
    timeout: 8000,
    fail() {
      // 日志上报必须 fail-open，不能影响业务。
    }
  });
}

function toErrorPayload(error) {
  if (!error) return undefined;
  if (error instanceof Error) {
    return {
      name: error.name || 'Error',
      message: error.message,
      stack: error.stack || ''
    };
  }
  if (typeof error === 'object') {
    return {
      name: error.errMsg ? 'WechatMiniappError' : 'Error',
      message: error.errMsg || safeJson(error),
      stack: ''
    };
  }
  return {
    name: 'Error',
    message: String(error),
    stack: ''
  };
}

function safeJson(value) {
  try {
    return JSON.stringify(value).slice(0, 1000);
  } catch (err) {
    return String(value).slice(0, 1000);
  }
}

function getSdkVersion() {
  try {
    const accountInfo = wx.getAccountInfoSync ? wx.getAccountInfoSync() : null;
    return accountInfo && accountInfo.miniProgram && accountInfo.miniProgram.version;
  } catch (err) {
    return '';
  }
  return '';
}

module.exports = {
  createTraceContext,
  childSpan,
  applyTraceHeaders,
  reportTraceLog
};
