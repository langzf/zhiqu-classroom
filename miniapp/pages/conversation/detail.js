const {
  downloadAudio,
  request,
  requestAudio,
  sendMessage,
  sendVoiceMessage
} = require('../../utils/request');
const { requireAuth } = require('../../utils/auth');
const { reportTraceLog } = require('../../utils/trace');

const recorder = wx.getRecorderManager();
let audioContext = null;

Page({
  data: {
    id: '',
    messages: [],
    input: '',
    sending: false,
    recording: false,
    voiceProfileId: null,
    autoPlay: false,
    playingMessageId: '',
    audioLoadingMessageId: '',
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
    if (this.data.sending) return;

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
    if (!res.tempFilePath || this.data.sending) return;

    const localVoice = {
      id: `local-voice-${Date.now()}`,
      role: 'user',
      content: '语音消息',
      metadata: {
        message_type: 'voice',
        audio: { url: res.tempFilePath, local: true }
      },
      created_at: new Date().toISOString()
    };
    this.setData({
      sending: true,
      messages: this.data.messages.concat(localVoice)
    }, this.scrollToBottom);

    try {
      const result = await sendVoiceMessage(this.data.id, res.tempFilePath);
      const nextMessages = this.data.messages
        .filter((item) => item.id !== localVoice.id)
        .concat(result.user_message, result.assistant_message);
      this.setData({ messages: nextMessages }, this.scrollToBottom);
      this.maybeAutoPlay(result.assistant_message);
    } catch (err) {
      wx.showToast({ title: err.message || '语音发送失败', icon: 'none' });
      this.setData({
        messages: this.data.messages.filter((item) => item.id !== localVoice.id)
      }, this.scrollToBottom);
    } finally {
      this.setData({ sending: false });
    }
  },

  async send() {
    const text = this.data.input.trim();
    if (!text || this.data.sending) return;

    const userMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: text,
      metadata: { message_type: 'text' },
      created_at: new Date().toISOString()
    };
    this.setData({
      input: '',
      sending: true,
      messages: this.data.messages.concat(userMessage)
    }, this.scrollToBottom);

    try {
      const result = await sendMessage(this.data.id, text);
      const nextMessages = this.data.messages
        .filter((item) => item.id !== userMessage.id)
        .concat(result.user_message, result.assistant_message);
      this.setData({ messages: nextMessages }, this.scrollToBottom);
      this.maybeAutoPlay(result.assistant_message);
    } catch (err) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' });
      this.setData({
        input: text,
        messages: this.data.messages.filter((item) => item.id !== userMessage.id)
      }, this.scrollToBottom);
    } finally {
      this.setData({ sending: false });
    }
  },

  playMessageAudio(event) {
    const messageId = event.currentTarget.dataset.id || event.target.dataset.id;
    if (this.data.playingMessageId === messageId && audioContext) {
      audioContext.stop();
      audioContext.destroy();
      audioContext = null;
      this.setData({ playingMessageId: '', audioLoadingMessageId: '' });
      return;
    }

    const message = this.data.messages.find((item) => item.id === messageId);
    if (!message) return;
    this.playAudioForMessage(message);
  },

  maybeAutoPlay(message) {
    if (this.data.autoPlay) {
      this.playAudioForMessage(message);
    }
  },

  async playAudioForMessage(message) {
    const audioMeta = message.metadata && message.metadata.audio;
    const audioUrl = audioMeta && audioMeta.url;
    if (!audioUrl && message.role === 'assistant') {
      return this.speakFallback(message);
    }
    if (!audioUrl) return;

    this.setData({ playingMessageId: message.id, audioLoadingMessageId: message.id });
    try {
      let filePath = audioUrl;
      if (!audioMeta.local) {
        const audio = await downloadAudio(audioUrl);
        filePath = `${wx.env.USER_DATA_PATH}/message-${message.id}.mp3`;
        wx.getFileSystemManager().writeFileSync(filePath, audio);
      }
      this.playLocalFile(filePath, message.id);
    } catch (err) {
      wx.showToast({ title: err.message || '播放失败', icon: 'none' });
      reportTraceLog('error', 'miniapp message audio playback prepare failed', {
        path: '/pages/conversation/detail',
        method: 'PLAY',
        error: err,
        meta: {
          messageId: message.id,
          hasAudioUrl: !!audioUrl,
          audioUrl,
          audioSource: audioMeta && audioMeta.source
        }
      });
      this.setData({ playingMessageId: '', audioLoadingMessageId: '' });
    }
  },

  async speakFallback(message) {
    if (!message.content) return;
    this.setData({ playingMessageId: message.id, audioLoadingMessageId: message.id });
    try {
      const audio = await requestAudio('/app/voice/tts', {
        text: message.content,
        voice_profile_id: this.data.voiceProfileId
      });
      const filePath = `${wx.env.USER_DATA_PATH}/speech-${Date.now()}.mp3`;
      wx.getFileSystemManager().writeFileSync(filePath, audio);
      this.playLocalFile(filePath, message.id);
    } catch (err) {
      wx.showToast({ title: err.message || '播放失败', icon: 'none' });
      reportTraceLog('error', 'miniapp assistant tts fallback failed', {
        path: '/pages/conversation/detail',
        method: 'PLAY',
        error: err,
        meta: {
          messageId: message.id,
          textLength: message.content.length,
          voiceProfileId: this.data.voiceProfileId
        }
      });
      this.setData({ playingMessageId: '', audioLoadingMessageId: '' });
    }
  },

  playLocalFile(filePath, messageId) {
    if (audioContext) {
      audioContext.destroy();
    }
    audioContext = wx.createInnerAudioContext();
    audioContext.src = filePath;
    audioContext.onCanplay(() => {
      this.setData({ audioLoadingMessageId: '' });
    });
    audioContext.onPlay(() => {
      this.setData({ playingMessageId: messageId, audioLoadingMessageId: '' });
    });
    audioContext.onEnded(() => this.setData({ playingMessageId: '', audioLoadingMessageId: '' }));
    audioContext.onStop(() => this.setData({ playingMessageId: '', audioLoadingMessageId: '' }));
    audioContext.onError((err) => {
      reportTraceLog('error', 'miniapp inner audio playback failed', {
        path: '/pages/conversation/detail',
        method: 'PLAY',
        error: err,
        meta: {
          messageId,
          filePath,
          errMsg: err && err.errMsg,
          errCode: err && err.errCode
        }
      });
      wx.showToast({ title: '播放失败', icon: 'none' });
      this.setData({ playingMessageId: '', audioLoadingMessageId: '' });
    });
    audioContext.play();
  }
});
