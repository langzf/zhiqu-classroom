const { request } = require('../../utils/request');
const { saveAuth, saveUser } = require('../../utils/auth');
const { reportTraceLog } = require('../../utils/trace');

function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (res.code) {
          resolve(res.code);
        } else {
          reject(new Error('未获取到微信登录凭证'));
        }
      },
      fail(err) {
        reportTraceLog('error', 'miniapp wx.login failed', {
          error: err,
          path: '/pages/login/index',
          method: 'WX_LOGIN',
          meta: {
            errMsg: err.errMsg
          }
        });
        reject(new Error(err.errMsg || '微信登录失败'));
      }
    });
  });
}

Page({
  data: {
    loading: false
  },

  async onWechatLogin() {
    this.setData({ loading: true });
    try {
      const code = await wxLogin();
      const data = await request({
        url: '/auth/wechat/miniapp/login',
        method: 'POST',
        data: { code }
      });
      saveAuth(data);
      try {
        const user = await request({ url: '/app/user/me' });
        saveUser(user);
      } catch (profileErr) {
        // The auth token is valid even if profile refresh fails briefly.
      }
      wx.switchTab({ url: '/pages/home/index' });
    } catch (err) {
      reportTraceLog('error', 'miniapp wechat login flow failed', {
        error: err,
        path: '/pages/login/index',
        method: 'LOGIN_FLOW',
        meta: {
          stage: 'wechat_login'
        }
      });
      wx.showToast({ title: err.message || '登录失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
