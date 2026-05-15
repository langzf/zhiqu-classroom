const { API_BASE_URL } = require('./config');
const { getToken, clearAuth } = require('./auth');
const {
  applyTraceHeaders,
  childSpan,
  createTraceContext,
  reportTraceLog
} = require('./trace');

function buildUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE_URL}${path}`;
}

function unwrap(body) {
  if (!body || typeof body !== 'object') return body;
  if (body.code !== 0) throw new Error(body.message || '请求失败');
  return body.data;
}

function parseResponseBody(data) {
  if (data && typeof data === 'object') return data;
  if (typeof data !== 'string' || !data) return null;
  try {
    return JSON.parse(data);
  } catch (err) {
    return null;
  }
}

function responseSnippet(data) {
  if (typeof data === 'string') return data.slice(0, 500);
  try {
    return JSON.stringify(data || {}).slice(0, 500);
  } catch (err) {
    return '';
  }
}

function errorMessage(prefix, statusCode, data) {
  const body = parseResponseBody(data);
  if (body && body.message) return body.message;
  return `${prefix} ${statusCode}`;
}

function elapsedMs(startedAt) {
  return Date.now() - startedAt;
}

function makeTrace() {
  return childSpan(createTraceContext());
}

function authHeader(traceContext, extraHeader) {
  const token = getToken();
  const header = Object.assign({}, extraHeader || {});
  applyTraceHeaders(header, traceContext);
  if (token) header.Authorization = `Bearer ${token}`;
  return header;
}

function handleUnauthorized(reject) {
  clearAuth();
  wx.redirectTo({ url: '/pages/login/index' });
  reject(new Error('登录已过期'));
}

function request(options) {
  const traceContext = makeTrace();
  const startedAt = Date.now();
  const url = buildUrl(options.url);
  const method = options.method || 'GET';
  const header = authHeader(traceContext, Object.assign({
    'content-type': 'application/json'
  }, options.header || {}));

  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method,
      data: options.data,
      header,
      timeout: options.timeout || 60000,
      responseType: options.responseType || 'text',
      success(res) {
        reportTraceLog(res.statusCode >= 400 ? 'warn' : 'info', 'miniapp request finished', {
          traceContext,
          path: options.url,
          method,
          statusCode: res.statusCode,
          durationMs: elapsedMs(startedAt),
          meta: {
            requestUrl: url,
            responseTraceId: res.header && (res.header['X-Trace-ID'] || res.header['x-trace-id'])
          }
        });

        if (res.statusCode === 401) {
          handleUnauthorized(reject);
          return;
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reportTraceLog(res.statusCode >= 500 ? 'error' : 'warn', 'miniapp request non-2xx', {
            traceContext,
            path: options.url,
            method,
            statusCode: res.statusCode,
            durationMs: elapsedMs(startedAt),
            meta: {
              requestUrl: url,
              responseBody: responseSnippet(res.data)
            }
          });
          reject(new Error(errorMessage('请求失败', res.statusCode, res.data)));
          return;
        }
        try {
          resolve(options.raw ? res : unwrap(res.data));
        } catch (err) {
          reportTraceLog('warn', 'miniapp response unwrap failed', {
            traceContext,
            path: options.url,
            method,
            statusCode: res.statusCode,
            durationMs: elapsedMs(startedAt),
            error: err,
            meta: { requestUrl: url }
          });
          reject(err);
        }
      },
      fail(err) {
        reportTraceLog('error', 'miniapp request failed', {
          traceContext,
          path: options.url,
          method,
          durationMs: elapsedMs(startedAt),
          error: err,
          meta: {
            requestUrl: url,
            errMsg: err.errMsg
          }
        });
        reject(new Error(err.errMsg || '网络异常'));
      }
    });
  });
}

function uploadFile(path, filePath, options) {
  const traceContext = makeTrace();
  const startedAt = Date.now();
  const url = buildUrl(path);
  const header = authHeader(traceContext, options && options.header);

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url,
      filePath,
      name: (options && options.name) || 'file',
      header,
      timeout: (options && options.timeout) || 120000,
      success(res) {
        reportTraceLog(res.statusCode >= 400 ? 'warn' : 'info', 'miniapp upload finished', {
          traceContext,
          path,
          method: 'POST',
          statusCode: res.statusCode,
          durationMs: elapsedMs(startedAt),
          meta: { requestUrl: url }
        });

        if (res.statusCode === 401) {
          handleUnauthorized(reject);
          return;
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reportTraceLog(res.statusCode >= 500 ? 'error' : 'warn', 'miniapp upload non-2xx', {
            traceContext,
            path,
            method: 'POST',
            statusCode: res.statusCode,
            durationMs: elapsedMs(startedAt),
            meta: {
              requestUrl: url,
              responseBody: responseSnippet(res.data)
            }
          });
          reject(new Error(errorMessage('上传失败', res.statusCode, res.data)));
          return;
        }
        try {
          resolve(unwrap(JSON.parse(res.data)));
        } catch (err) {
          reportTraceLog('warn', 'miniapp upload unwrap failed', {
            traceContext,
            path,
            method: 'POST',
            statusCode: res.statusCode,
            durationMs: elapsedMs(startedAt),
            error: err,
            meta: { requestUrl: url }
          });
          reject(err);
        }
      },
      fail(err) {
        reportTraceLog('error', 'miniapp upload failed', {
          traceContext,
          path,
          method: 'POST',
          durationMs: elapsedMs(startedAt),
          error: err,
          meta: {
            requestUrl: url,
            errMsg: err.errMsg
          }
        });
        reject(new Error(err.errMsg || '上传失败'));
      }
    });
  });
}

function uploadAudio(path, filePath) {
  return uploadFile(path, filePath);
}

function sendVoiceMessage(conversationId, filePath) {
  return uploadFile(`/app/tutor/conversations/${conversationId}/voice-messages`, filePath);
}

function requestAudio(path, data) {
  return request({
    url: path,
    method: 'POST',
    data,
    responseType: 'arraybuffer',
    raw: true,
    timeout: 120000
  }).then((res) => res.data);
}

function downloadAudio(path) {
  return request({
    url: path,
    method: 'GET',
    responseType: 'arraybuffer',
    raw: true,
    timeout: 120000
  }).then((res) => res.data);
}

function sendMessage(conversationId, content) {
  return request({
    url: `/app/tutor/conversations/${conversationId}/messages/sync`,
    method: 'POST',
    data: { content },
    timeout: 180000
  });
}

module.exports = {
  request,
  uploadAudio,
  requestAudio,
  downloadAudio,
  sendMessage,
  sendVoiceMessage
};
