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
  if (!body || typeof body !== 'object') {
    return body;
  }
  if (body.code !== 0) {
    throw new Error(body.message || '请求失败');
  }
  return body.data;
}

function elapsedMs(startedAt) {
  return Date.now() - startedAt;
}

function makeTrace() {
  return childSpan(createTraceContext());
}

function request(options) {
  const token = getToken();
  const traceContext = makeTrace();
  const startedAt = Date.now();
  const url = buildUrl(options.url);
  const method = options.method || 'GET';
  const header = Object.assign({
    'content-type': 'application/json'
  }, options.header || {});

  applyTraceHeaders(header, traceContext);
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

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
          clearAuth();
          wx.redirectTo({ url: '/pages/login/index' });
          reject(new Error('登录已过期'));
          return;
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`请求失败 ${res.statusCode}`));
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

function uploadAudio(path, filePath) {
  const token = getToken();
  const traceContext = makeTrace();
  const startedAt = Date.now();
  const url = buildUrl(path);
  const header = token ? { Authorization: `Bearer ${token}` } : {};

  applyTraceHeaders(header, traceContext);

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url,
      filePath,
      name: 'file',
      header,
      timeout: 120000,
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
          clearAuth();
          wx.redirectTo({ url: '/pages/login/index' });
          reject(new Error('登录已过期'));
          return;
        }
        try {
          const body = JSON.parse(res.data);
          resolve(unwrap(body));
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

function parseSseText(raw) {
  if (!raw) return '';
  const text = typeof raw === 'string' ? raw : String(raw);
  let fullText = '';
  text.split('\n').forEach((line) => {
    if (!line.startsWith('data: ')) return;
    const data = line.slice(6).trim();
    if (!data || data === '[DONE]') return;
    try {
      const parsed = JSON.parse(data);
      const delta = parsed && parsed.choices && parsed.choices[0] && parsed.choices[0].delta;
      fullText += parsed && (parsed.content || parsed.text || (delta && delta.content) || '');
    } catch (err) {
      fullText += data;
    }
  });
  return fullText || text;
}

function sendMessage(conversationId, content) {
  return request({
    url: `/app/tutor/conversations/${conversationId}/messages`,
    method: 'POST',
    data: { content },
    raw: true,
    timeout: 120000
  }).then((res) => parseSseText(res.data));
}

module.exports = {
  request,
  uploadAudio,
  requestAudio,
  sendMessage,
  parseSseText
};
