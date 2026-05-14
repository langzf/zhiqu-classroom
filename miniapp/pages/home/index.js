const { request } = require('../../utils/request');
const { requireAuth } = require('../../utils/auth');

Page({
  data: {
    loading: true,
    tasks: []
  },

  onShow() {
    if (!requireAuth()) return;
    this.loadData();
  },

  onPullDownRefresh() {
    this.loadData().finally(() => wx.stopPullDownRefresh());
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const data = await request({
        url: '/app/learning/tasks',
        data: { page: 1, page_size: 5 }
      });
      const tasks = (data.items || []).map((item) => ({
        ...item,
        hasProgress: item.progress_pct !== null && item.progress_pct !== undefined
      }));
      this.setData({ tasks });
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  goChat() {
    wx.switchTab({ url: '/pages/chat/index' });
  }
});
