import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConversation, listMessages, sendMessageStream } from '@/api/tutor';
import { getVoiceSetting, synthesizeSpeech, transcribeAudio } from '@/api/voice';
import { reportTraceLog } from '@/api/trace';
import type { Conversation, Message } from '@zhiqu/shared';
import './ConversationPage.css';

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [conv, setConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [streamingText, setStreamingText] = useState('');
  const [voiceProfileId, setVoiceProfileId] = useState<string | null>(null);
  const [autoPlayVoice, setAutoPlayVoice] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([getConversation(id), listMessages(id)])
      .then(([c, paginated]) => {
        setConv(c);
        if (!Array.isArray(paginated.items)) {
          reportTraceLog('error', 'frontend invalid messages payload', {
            path: `/conversation/${id}`,
            meta: {
              app: 'student',
              conversationId: id,
              payloadType: typeof paginated,
              payloadKeys: paginated && typeof paginated === 'object' ? Object.keys(paginated).join(',') : '',
              itemsType: typeof paginated.items,
            },
          });
        }
        setMessages(Array.isArray(paginated.items) ? paginated.items : []);
      })
      .catch(() => navigate('/chat', { replace: true }))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  useEffect(() => {
    getVoiceSetting()
      .then((setting) => {
        setVoiceProfileId(setting.voice_profile_id);
        setAutoPlayVoice(setting.auto_play);
      })
      .catch(() => {
        setVoiceProfileId(null);
        setAutoPlayVoice(false);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
    };
  }, []);

  async function playAssistantText(text: string, messageId: string) {
    if (!text.trim()) return;
    setSpeakingMessageId(messageId);
    try {
      const audio = await synthesizeSpeech(text, voiceProfileId);
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
      audioUrlRef.current = URL.createObjectURL(audio);
      const player = new Audio(audioUrlRef.current);
      player.onended = () => setSpeakingMessageId(null);
      player.onerror = () => setSpeakingMessageId(null);
      await player.play();
    } catch (err) {
      console.error('play voice failed', err);
      setSpeakingMessageId(null);
    }
  }

  async function handleVoiceInput() {
    if (recording) {
      mediaRecorderRef.current?.stop();
      return;
    }
    if (sending || transcribing) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        const audio = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        if (!audio.size) return;
        setTranscribing(true);
        try {
          const result = await transcribeAudio(audio);
          if (result.text) {
            setInput((prev) => `${prev}${prev ? ' ' : ''}${result.text}`);
          }
        } catch (err) {
          console.error('transcribe voice failed', err);
        } finally {
          setTranscribing(false);
        }
      };

      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error('start recording failed', err);
      setRecording(false);
    }
  }

  async function handleSend() {
    if (!id || !input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setSending(true);
    setStreamingText('');

    const tempUserMsg: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: id,
      role: 'user',
      content: text,
      token_count: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    await sendMessageStream(
      id,
      text,
      (chunk) => {
        setStreamingText((prev) => prev + chunk);
      },
      (fullText) => {
        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          conversation_id: id,
          role: 'assistant',
          content: fullText,
          token_count: null,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setStreamingText('');
        setSending(false);
        if (autoPlayVoice) {
          void playAssistantText(fullText, aiMsg.id);
        }
      },
      () => {
        setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
        setInput(text);
        setStreamingText('');
        setSending(false);
      },
    );
  }

  if (loading) {
    return <div className="loading-center"><div className="spinner" /></div>;
  }

  const safeMessages = Array.isArray(messages) ? messages : [];

  return (
    <div className="conversation-page">
      <header className="conv-header">
        <button className="back-btn" onClick={() => navigate('/chat')}>返回</button>
        <h1>{conv?.title || '对话'}</h1>
      </header>

      <div className="message-list">
        {safeMessages.length === 0 && (
          <div className="empty-hint">开始你的第一句提问吧</div>
        )}
        {safeMessages.map((msg) => (
          <div key={msg.id} className={`msg-bubble ${msg.role}`}>
            <div className="msg-role">
              {msg.role === 'user' ? '我' : 'AI'}
              {msg.role === 'assistant' && (
                <button
                  type="button"
                  className="speak-btn"
                  onClick={() => playAssistantText(msg.content, msg.id)}
                  disabled={speakingMessageId === msg.id}
                >
                  {speakingMessageId === msg.id ? '播放中' : '播放'}
                </button>
              )}
            </div>
            <div className="msg-content">{msg.content}</div>
          </div>
        ))}
        {streamingText && (
          <div className="msg-bubble assistant streaming">
            <div className="msg-role">AI</div>
            <div className="msg-content">{streamingText}<span className="cursor-blink">|</span></div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <button
          type="button"
          className={`voice-btn ${recording ? 'recording' : ''}`}
          onClick={handleVoiceInput}
          disabled={sending || transcribing}
          title={recording ? '停止录音' : '语音输入'}
        >
          {recording ? '停' : transcribing ? '转' : '麦'}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={transcribing ? '正在识别语音...' : '输入你的问题...'}
          disabled={sending}
        />
        <button onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? '...' : '发送'}
        </button>
      </div>
    </div>
  );
}

Component.displayName = 'ConversationPage';
