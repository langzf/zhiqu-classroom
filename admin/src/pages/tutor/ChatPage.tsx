import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Card, Input, Button, Space, Spin, message, Typography, Divider, Tag, Empty, Select,
} from 'antd';
import { AudioOutlined, SendOutlined, ArrowLeftOutlined, SoundOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getConversation,
  listMessages,
  sendMessageStream,
  sendMessage,
  type Conversation,
  type Message,
} from '@/api/tutor';
import { listVoiceProfiles, synthesizeSpeech, transcribeAudio } from '@/api/voice';
import type { VoiceProfile } from '@zhiqu/shared';

const { Text, Paragraph } = Typography;

export default function ChatPage() {
  const { id: convId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [inputText, setInputText] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [selectedVoiceProfileId, setSelectedVoiceProfileId] = useState<string | undefined>();
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioUrlRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchData = useCallback(async () => {
    if (!convId) return;
    setLoading(true);
    try {
      const [conv, msgRes, profiles] = await Promise.all([
        getConversation(convId),
        listMessages(convId, { page: 1, page_size: 100 }),
        listVoiceProfiles(false),
      ]);
      setConversation(conv);
      setMessages(msgRes.items);
      setVoiceProfiles(profiles);
      setSelectedVoiceProfileId((current) => current || profiles[0]?.id);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [convId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
    };
  }, []);

  const playAssistantText = async (text: string, messageId: string) => {
    if (!text.trim()) return;
    setSpeakingMessageId(messageId);
    try {
      const audio = await synthesizeSpeech(text, selectedVoiceProfileId);
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
      audioUrlRef.current = URL.createObjectURL(audio);
      const player = new Audio(audioUrlRef.current);
      player.onended = () => setSpeakingMessageId(null);
      player.onerror = () => setSpeakingMessageId(null);
      await player.play();
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '语音播放失败');
      setSpeakingMessageId(null);
    }
  };

  const handleVoiceInput = async () => {
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
            setInputText((prev) => `${prev}${prev ? ' ' : ''}${result.text}`);
          }
        } catch (err: unknown) {
          message.error(err instanceof Error ? err.message : '语音识别失败');
        } finally {
          setTranscribing(false);
        }
      };

      recorder.start();
      setRecording(true);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '无法启动录音');
      setRecording(false);
    }
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || !convId || sending) return;

    const tempUserMsg: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: convId,
      role: 'user',
      content: text,
      tokens_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setInputText('');
    setSending(true);
    setStreamingText('');

    try {
      let useStreaming = true;
      await sendMessageStream(
        convId,
        text,
        (chunk) => {
          setStreamingText((prev) => prev + chunk);
        },
        (fullText) => {
          setStreamingText('');
          const assistantMsg: Message = {
            id: `temp-assistant-${Date.now()}`,
            conversation_id: convId,
            role: 'assistant',
            content: fullText,
            tokens_used: null,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setSending(false);
        },
        async () => {
          useStreaming = false;
          try {
            setStreamingText('');
            const result = await sendMessage(convId, text);
            setMessages((prev) => {
              const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
              return [...withoutTemp, result.user_message, result.assistant_message];
            });
          } catch (innerErr: unknown) {
            message.error(innerErr instanceof Error ? innerErr.message : '发送失败');
          } finally {
            setSending(false);
          }
        },
      );
      if (!useStreaming) return;
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '发送失败');
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderMessage = (msg: Message) => {
    const isUser = msg.role === 'user';
    const isSystem = msg.role === 'system';

    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 16,
        }}
      >
        <div
          style={{
            maxWidth: '70%',
            padding: '12px 16px',
            borderRadius: 12,
            background: isUser ? '#4F46E5' : isSystem ? '#f0f0f0' : '#fff',
            color: isUser ? '#fff' : '#333',
            border: isUser ? 'none' : '1px solid #e8e8e8',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}
        >
          {isSystem && (
            <Tag color="default" style={{ marginBottom: 4 }}>
              系统
            </Tag>
          )}
          <Paragraph
            style={{
              margin: 0,
              color: isUser ? '#fff' : '#333',
              whiteSpace: 'pre-wrap',
            }}
          >
            {msg.content}
          </Paragraph>
          <Space size={8} style={{ width: '100%', justifyContent: 'space-between', marginTop: 4 }}>
            {!isUser && !isSystem ? (
              <Button
                size="small"
                type="link"
                icon={<SoundOutlined />}
                onClick={() => playAssistantText(msg.content, msg.id)}
                loading={speakingMessageId === msg.id}
                style={{ padding: 0 }}
              >
                播放
              </Button>
            ) : <span />}
            <Text
              type="secondary"
              style={{
                fontSize: 11,
                color: isUser ? 'rgba(255,255,255,0.7)' : undefined,
              }}
            >
              {new Date(msg.created_at).toLocaleTimeString('zh-CN')}
            </Text>
          </Space>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" tip="加载对话中..." />
      </div>
    );
  }

  return (
    <Card
      title={
        <Space>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/tutor')}
          />
          <span>{conversation?.title || '对话'}</span>
          {conversation?.scene && <Tag>{conversation.scene}</Tag>}
        </Space>
      }
      extra={
        <Select
          size="small"
          style={{ width: 180 }}
          placeholder="选择播报音色"
          allowClear
          value={selectedVoiceProfileId}
          onChange={setSelectedVoiceProfileId}
          options={voiceProfiles.map((profile) => ({ label: profile.name, value: profile.id }))}
        />
      }
      bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}
    >
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 24px',
          background: '#fafafa',
        }}
      >
        {messages.length === 0 && !streamingText ? (
          <Empty description="暂无消息，发送第一条消息开始对话" style={{ marginTop: 60 }} />
        ) : (
          <>
            {messages.map(renderMessage)}
            {streamingText && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                <div
                  style={{
                    maxWidth: '70%',
                    padding: '12px 16px',
                    borderRadius: 12,
                    background: '#fff',
                    border: '1px solid #e8e8e8',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                  }}
                >
                  <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                    {streamingText}
                    <span className="typing-cursor">|</span>
                  </Paragraph>
                </div>
              </div>
            )}
            {sending && !streamingText && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                <Spin size="small" />
                <Text type="secondary" style={{ marginLeft: 8 }}>思考中...</Text>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <Divider style={{ margin: 0 }} />

      <div style={{ padding: '12px 24px', background: '#fff' }}>
        <Space.Compact style={{ width: '100%' }}>
          <Button
            icon={<AudioOutlined />}
            onClick={handleVoiceInput}
            loading={transcribing}
            danger={recording}
            disabled={sending}
            style={{ height: 'auto', borderRadius: '8px 0 0 8px' }}
          >
            {recording ? '停止' : '语音'}
          </Button>
          <Input.TextArea
            ref={inputRef as React.Ref<unknown> as React.Ref<HTMLTextAreaElement>}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={transcribing ? '正在识别语音...' : '输入消息... (Enter 发送，Shift+Enter 换行)'}
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={sending}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={sending}
            disabled={!inputText.trim()}
            style={{ height: 'auto', borderRadius: '0 8px 8px 0' }}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </Card>
  );
}
