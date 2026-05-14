const { request } = require('../../utils/request');
const { requireAuth } = require('../../utils/auth');
const { formatDateTime, sceneLabel } = require('../../utils/format');

Page({
  data: {
    loading: true,
    creating: false,
    conversations: []
  },

  onShow() {
    if (!requireAuth()) return;
    this.loadConversations();
  },

  onPullDownRefresh() {
    this.loadConversations().finally(() => wx.stopPullDownRefresh());
  },

  async loadConversations() {
    this.setData({ loading: true });
    try {
      const data = await request({
        url: '/app/tutor/conversations',
        data: { page: 1, page_size: 30 }
      });
      const conversations = (data.items || []).map((item) => ({
        ...item,
        sceneLabel: sceneLabel(item.scene),
        timeText: formatDateTime(item.last_message_at || item.updated_at || item.created_at)
      }));
      this.setData({ conversations });
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  async createConversation() {
    this.setData({ creating: true });
    try {
      const conv = await request({
        url: '/app/tutor/conversations',
        method: 'POST',
        data: {
          scene: 'free_chat',
          title: `新对话 ${new Date().toLocaleString()}`
        }
      });
      wx.navigateTo({ url: `/pages/conversation/detail?id=${conv.id}` });
    } catch (err) {
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    } finally {
      this.setData({ creating: false });
    }
  },

  openConversation(event) {
    wx.navigateTo({ url: `/pages/conversation/detail?id=${event.currentTarget.dataset.id}` });
  }
});
