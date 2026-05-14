const { STORAGE_KEYS } = require('./config');

function getToken() {
  return wx.getStorageSync(STORAGE_KEYS.token) || '';
}

function getUser() {
  return wx.getStorageSync(STORAGE_KEYS.user) || null;
}

function saveAuth(data) {
  wx.setStorageSync(STORAGE_KEYS.token, data.access_token || '');
  wx.setStorageSync(STORAGE_KEYS.refreshToken, data.refresh_token || '');
  if (data.user) {
    saveUser(data.user);
  }
}

function saveUser(user) {
  wx.setStorageSync(STORAGE_KEYS.user, user || null);
}

function clearAuth() {
  wx.removeStorageSync(STORAGE_KEYS.token);
  wx.removeStorageSync(STORAGE_KEYS.refreshToken);
  wx.removeStorageSync(STORAGE_KEYS.user);
}

function requireAuth() {
  if (getToken()) {
    return true;
  }
  wx.redirectTo({ url: '/pages/login/index' });
  return false;
}

module.exports = {
  getToken,
  getUser,
  saveAuth,
  saveUser,
  clearAuth,
  requireAuth
};
