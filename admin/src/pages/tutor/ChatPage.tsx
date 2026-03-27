import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Input, Button, Space, Spin, message, Card, Tag, Descriptions,
} from 'antd';
import {
  ArrowLeftOutlined, SendOutlined,
} from '@ant-design/icons';
import { getConversation, listMessages, sendMessage } from '@/api/tutor';
import type { Conversation, Message as Msg } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [conv, setConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchConv = useCallback(async () => {
    if (!id) return;
    try {
      const [c, msgs] = await Promise.all([
        getConversation(id),
        listMessages(id, { limit: 100 }),
      ]);
      setConv(c);
      setMessages(msgs);
    } catch {
      message.error('加载会话失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchConv(); }, [fetchConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!inputText.trim() || !id) return;
    const content = inputText.trim();
    setInputText('');
    setSending(true);

    // Optimistic user message
    const tempMsg: Msg = {
      id: `temp-${Date.now()}`,
      conversation_id: id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempMsg]);

    try {
      const reply = await sendMessage(id, content);
      // Replace temp + add AI reply
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== tempMsg.id);
        return [...filtered, { ...tempMsg, id: reply.id ? `user-${reply.id}` : tempMsg.id }, reply];
      });
    } catch {
      message.error('发送失败');
      // Remove temp message on failure
      setMessages(prev => prev.filter(m => m.id !== tempMsg.id));
      setInputText(content);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }

  const isActive = conv?.status === 'active';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 'calc(100vh - 160px)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tutor')}>返回</Button>
        <Title level={4} style={{ margin: 0, flex: 1 }}>
          {conv?.title || '对话'}
        </Title>
        <Tag color={isActive ? 'green' : 'default'}>
          {isActive ? '进行中' : '已归档'}
        </Tag>
      </div>

      {conv?.subject && (
        <Descriptions size="small" column={3} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="科目">{conv.subject}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDate(conv.created_at)}</Descriptions.Item>
          <Descriptions.Item label="消息数">{messages.length}</Descriptions.Item>
        </Descriptions>
      )}

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 16,
          background: '#f5f5f5',
          borderRadius: 8,
          marginBottom: 16,
          minHeight: 300,
        }}
      >
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">开始你的 AI 辅导对话吧 👋</Text>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                marginBottom: 12,
              }}
            >
              <Card
                size="small"
                style={{
                  maxWidth: '70%',
                  background: isUser ? '#1677ff' : '#fff',
                  border: isUser ? 'none' : '1px solid #e8e8e8',
                }}
                bodyStyle={{ padding: '8px 12px' }}
              >
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text
                      strong
                      style={{ fontSize: 12, color: isUser ? 'rgba(255,255,255,0.8)' : '#999' }}
                    >
                      {isUser ? '我' : 'AI 助教'}
                    </Text>
                    <Text
                      style={{ fontSize: 11, color: isUser ? 'rgba(255,255,255,0.6)' : '#ccc' }}
                    >
                      {formatDate(msg.created_at)}
                    </Text>
                  </div>
                  <Paragraph
                    style={{
                      margin: 0,
                      color: isUser ? '#fff' : '#333',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.content}
                  </Paragraph>
                </Space>
              </Card>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {isActive ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题... (Enter 发送，Shift+Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={sending}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={sending}
            disabled={!inputText.trim()}
          >
            发送
          </Button>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 12, color: '#999' }}>
          此会话已归档，无法继续对话
        </div>
      )}
    </div>
  );
}
