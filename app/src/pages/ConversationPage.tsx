import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConversation, listMessages, sendMessageStream } from '@/api/tutor';
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
  const bottomRef = useRef<HTMLDivElement>(null);

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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

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
            <div className="msg-role">{msg.role === 'user' ? '我' : 'AI'}</div>
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
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="输入你的问题..."
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
