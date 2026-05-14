const { request } = require('../../utils/request');
const { getUser, saveUser, clearAuth, requireAuth } = require('../../utils/auth');

Page({
  data: {
    user: {},
    avatarText: '知',
    profiles: [],
    profileNames: ['默认音色'],
    selectedIndex: 0,
    selectedName: '默认音色',
    voiceProfileId: null,
    autoPlay: false
  },

  onShow() {
    if (!requireAuth()) return;
    const user = getUser() || {};
    this.setData({
      user,
      avatarText: (user.nickname || '知').slice(0, 1)
    });
    this.loadUser();
    this.loadVoiceData();
  },

  async loadUser() {
    try {
      const user = await request({ url: '/app/user/me' });
      saveUser(user);
      this.setData({
        user,
        avatarText: (user.nickname || '知').slice(0, 1)
      });
    } catch (err) {
      // Keep cached user info.
    }
  },

  async loadVoiceData() {
    try {
      const [profiles, setting] = await Promise.all([
        request({ url: '/app/voice/profiles' }),
        request({ url: '/app/voice/settings' })
      ]);
      const names = ['默认音色'].concat((profiles || []).map((item) => item.name));
      const profileId = setting.voice_profile_id || null;
      const selectedIndex = profileId ? Math.max(0, (profiles || []).findIndex((item) => item.id === profileId) + 1) : 0;
      this.setData({
        profiles: profiles || [],
        profileNames: names,
        selectedIndex,
        selectedName: names[selectedIndex] || '默认音色',
        voiceProfileId: profileId,
        autoPlay: !!setting.auto_play
      });
    } catch (err) {
      wx.showToast({ title: err.message || '语音设置加载失败', icon: 'none' });
    }
  },

  async onVoiceChange(event) {
    const index = Number(event.detail.value || 0);
    const profile = index > 0 ? this.data.profiles[index - 1] : null;
    await this.saveSetting(profile ? profile.id : null, this.data.autoPlay);
  },

  async onAutoPlayChange(event) {
    await this.saveSetting(this.data.voiceProfileId, !!event.detail.value);
  },

  async saveSetting(voiceProfileId, autoPlay) {
    try {
      const setting = await request({
        url: '/app/voice/settings',
        method: 'PATCH',
        data: {
          voice_profile_id: voiceProfileId,
          auto_play: autoPlay
        }
      });
      const selectedIndex = setting.voice_profile_id
        ? Math.max(0, this.data.profiles.findIndex((item) => item.id === setting.voice_profile_id) + 1)
        : 0;
      this.setData({
        selectedIndex,
        selectedName: this.data.profileNames[selectedIndex] || '默认音色',
        voiceProfileId: setting.voice_profile_id || null,
        autoPlay: !!setting.auto_play
      });
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' });
    }
  },

  logout() {
    clearAuth();
    wx.redirectTo({ url: '/pages/login/index' });
  }
});
