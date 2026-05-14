const { getToken } = require('./utils/auth');

App({
  globalData: {
    apiBaseUrl: 'https://zqback.yueying.cloud/api/v1'
  },

  onLaunch() {
    const token = getToken();
    if (!token) {
      return;
    }
  }
});
