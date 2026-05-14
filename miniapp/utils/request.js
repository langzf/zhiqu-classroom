const { API_BASE_URL } = require('./config');
const { getToken, clearAuth } = require('./auth');

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

function request(options) {
  const token = getToken();
  const header = Object.assign({
    'content-type': 'application/json'
  }, options.header || {});
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl(options.url),
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: options.timeout || 60000,
      responseType: options.responseType || 'text',
      success(res) {
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
          reject(err);
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络异常'));
      }
    });
  });
}

function uploadAudio(path, filePath) {
  const token = getToken();
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: buildUrl(path),
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      timeout: 120000,
      success(res) {
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
          reject(err);
        }
      },
      fail(err) {
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
