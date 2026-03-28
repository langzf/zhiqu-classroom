import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConversation, listMessages, sendMessage } from '@/api/tutor';
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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([getConversation(id), listMessages(id)])
      .then(([c, msgs]) => {
        setConv(c);
        setMessages(msgs);
      })
      .catch(() => navigate('/chat', { replace: true }))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    if (!id || !input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setSending(true);

    // optimistic: show user message immediately
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: id,
      role: 'user',
      content: text,
      token_count: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const resp = await sendMessage(id, text);
      // replace temp msg with real user_msg and add assistant_msg
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        resp.user_msg,
        resp.assistant_msg,
      ]);
    } catch {
      // remove temp msg on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
      setInput(text); // restore input
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return <div className="loading-center"><div className="spinner" /></div>;
  }

  return (
    <div className="conversation-page">
      <header className="conv-header">
        <button className="back-btn" onClick={() => navigate('/chat')}>←</button>
        <h1>{conv?.title || '对话'}</h1>
      </header>

      <div className="message-list">
        {messages.length === 0 && (
          <div className="empty-hint">开始你的第一句提问吧 ✨</div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`msg-bubble ${msg.role}`}>
            <div className="msg-role">{msg.role === 'user' ? '我' : 'AI'}</div>
            <div className="msg-content">{msg.content}</div>
          </div>
        ))}
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
