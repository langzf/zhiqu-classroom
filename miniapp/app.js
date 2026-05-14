const { getToken } = require('./utils/auth');
const { reportTraceLog } = require('./utils/trace');

App({
  globalData: {
    apiBaseUrl: 'https://zqback.yueying.cloud/api/v1'
  },

  onLaunch() {
    const token = getToken();
    if (!token) {
      return;
    }
  },

  onError(error) {
    reportTraceLog('error', 'miniapp app error', {
      error: new Error(error || 'miniapp app error')
    });
  },

  onUnhandledRejection(event) {
    reportTraceLog('error', 'miniapp unhandled rejection', {
      error: event && event.reason ? event.reason : new Error('unhandled rejection')
    });
  }
});
