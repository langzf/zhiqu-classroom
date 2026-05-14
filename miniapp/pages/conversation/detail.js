const { request, uploadAudio, requestAudio, sendMessage } = require('../../utils/request');
const { requireAuth } = require('../../utils/auth');

const recorder = wx.getRecorderManager();
let audioContext = null;

Page({
  data: {
    id: '',
    messages: [],
    input: '',
    loading: true,
    sending: false,
    recording: false,
    transcribing: false,
    voiceProfileId: null,
    autoPlay: false,
    scrollIntoView: ''
  },

  onLoad(options) {
    if (!requireAuth()) return;
    this.setData({ id: options.id || '' });
    recorder.onStop(this.onRecordStop.bind(this));
    recorder.onError(() => {
      this.setData({ recording: false });
      wx.showToast({ title: '录音失败', icon: 'none' });
    });
    this.loadData();
    this.loadVoiceSetting();
  },

  onUnload() {
    if (audioContext) {
      audioContext.destroy();
      audioContext = null;
    }
  },

  async loadData() {
    if (!this.data.id) return;
    try {
      const data = await request({
        url: `/app/tutor/conversations/${this.data.id}/messages`,
        data: { page: 1, page_size: 100 }
      });
      this.setData({ messages: data.items || [] }, this.scrollToBottom);
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
    }
  },

  async loadVoiceSetting() {
    try {
      const setting = await request({ url: '/app/voice/settings' });
      this.setData({
        voiceProfileId: setting.voice_profile_id || null,
        autoPlay: !!setting.auto_play
      });
    } catch (err) {
      this.setData({ voiceProfileId: null, autoPlay: false });
    }
  },

  onInput(event) {
    this.setData({ input: event.detail.value });
  },

  scrollToBottom() {
    const index = Math.max(this.data.messages.length - 1, 0);
    this.setData({ scrollIntoView: `msg-${index}` });
  },

  toggleRecord() {
    if (this.data.recording) {
      recorder.stop();
      return;
    }
    wx.authorize({
      scope: 'scope.record',
      success: () => {
        recorder.start({
          duration: 60000,
          sampleRate: 16000,
          numberOfChannels: 1,
          encodeBitRate: 48000,
          format: 'mp3'
        });
        this.setData({ recording: true });
      },
      fail: () => wx.showToast({ title: '请允许录音权限', icon: 'none' })
    });
  },

  async onRecordStop(res) {
    this.setData({ recording: false });
    if (!res.tempFilePath) return;
    this.setData({ transcribing: true });
    try {
      const data = await uploadAudio('/app/voice/stt', res.tempFilePath);
      if (data.text) {
        this.setData({ input: `${this.data.input}${this.data.input ? ' ' : ''}${data.text}` });
      }
    } catch (err) {
      wx.showToast({ title: err.message || '识别失败', icon: 'none' });
    } finally {
      this.setData({ transcribing: false });
    }
  },

  async send() {
    const text = this.data.input.trim();
    if (!text || this.data.sending) return;

    const userMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    this.setData({
      input: '',
      sending: true,
      messages: this.data.messages.concat(userMessage)
    }, this.scrollToBottom);

    try {
      const answer = await sendMessage(this.data.id, text);
      const assistant = {
        id: `local-ai-${Date.now()}`,
        role: 'assistant',
        content: answer || '我暂时没有生成回复，请稍后再试。',
        created_at: new Date().toISOString()
      };
      this.setData({
        messages: this.data.messages.concat(assistant)
      }, this.scrollToBottom);
      if (this.data.autoPlay) {
        this.speak(assistant.content);
      }
    } catch (err) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' });
      this.setData({ input: text });
    } finally {
      this.setData({ sending: false });
    }
  },

  playText(event) {
    this.speak(event.currentTarget.dataset.text || '');
  },

  async speak(text) {
    if (!text) return;
    wx.showLoading({ title: '生成语音' });
    try {
      const audio = await requestAudio('/app/voice/tts', {
        text,
        voice_profile_id: this.data.voiceProfileId
      });
      const filePath = `${wx.env.USER_DATA_PATH}/speech-${Date.now()}.mp3`;
      wx.getFileSystemManager().writeFileSync(filePath, audio);
      if (audioContext) {
        audioContext.destroy();
      }
      audioContext = wx.createInnerAudioContext();
      audioContext.src = filePath;
      audioContext.play();
    } catch (err) {
      wx.showToast({ title: err.message || '播放失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  }
});
