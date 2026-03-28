import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { listConversations, createConversation } from '@/api/tutor';
import { Loading, Empty } from '@/components/Feedback';
import type { Conversation } from '@zhiqu/shared';

export function Component() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listConversations()
      .then((res) => setConversations(res.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleNew = async () => {
    setCreating(true);
    try {
      const conv = await createConversation({ scene: 'free_chat', title: '新对话' });
      navigate(`/conversation/${conv.id}`);
    } catch {
      /* ignore */
    }
    setCreating(false);
  };

  if (loading) return <Loading />;

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <h2 style={{ fontSize: 'var(--font-xl)', fontWeight: 600 }}>AI 辅导</h2>
        <button
          className="btn btn-primary"
          onClick={handleNew}
          disabled={creating}
          style={{ height: 36, fontSize: 'var(--font-sm)' }}
        >
          {creating ? '创建中...' : '+ 新对话'}
        </button>
      </div>

      {conversations.length === 0 ? (
        <Empty text="还没有对话，开始第一次提问吧" icon="💬" />
      ) : (
        conversations.map((conv) => (
          <div
            key={conv.id}
            className="card"
            onClick={() => navigate(`/conversation/${conv.id}`)}
            style={{ marginBottom: 'var(--spacing-md)', cursor: 'pointer' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>
                  💬 {conv.title || '对话'}
                </div>
                <div style={{ fontSize: 'var(--font-xs)', color: 'var(--color-text-tertiary)' }}>
                  {conv.scene === 'free_chat' ? '自由问答' :
                   conv.scene === 'concept_explain' ? '概念讲解' :
                   conv.scene === 'homework_help' ? '作业辅导' :
                   conv.scene === 'review_guide' ? '复习引导' :
                   conv.scene === 'error_analysis' ? '错题分析' : conv.scene}
                </div>
              </div>
              <span style={{ color: 'var(--color-text-tertiary)' }}>→</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

Component.displayName = 'ChatPage';
