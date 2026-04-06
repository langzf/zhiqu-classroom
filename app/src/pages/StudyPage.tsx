import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { listTextbooks } from '@/api/content';
import { listTasks } from '@/api/learning';
import { Loading, Empty } from '@/components/Feedback';
import type { Textbook, LearningTask } from '@zhiqu/shared';

type Tab = 'textbooks' | 'tasks';

export function Component() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('textbooks');

  return (
    <div>
      {/* Tab Switch */}
      <div
        style={{
          display: 'flex', background: 'var(--color-bg-white)',
          borderBottom: '1px solid var(--color-border-light)',
          position: 'sticky', top: 0, zIndex: 10,
        }}
      >
        {[
          { key: 'textbooks' as Tab, label: '教材' },
          { key: 'tasks' as Tab, label: '学习任务' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1, padding: 'var(--spacing-md) 0', border: 'none', background: 'none',
              fontWeight: tab === t.key ? 600 : 400,
              color: tab === t.key ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              borderBottom: tab === t.key ? '2px solid var(--color-primary)' : '2px solid transparent',
              fontSize: 'var(--font-md)',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ padding: 'var(--spacing-lg)' }}>
        {tab === 'textbooks' ? (
          <TextbookList onSelect={(id) => navigate(`/textbook/${id}`)} />
        ) : (
          <TaskList onSelect={(id) => navigate(`/task/${id}`)} />
        )}
      </div>
    </div>
  );
}

Component.displayName = 'StudyPage';

/* ── Textbook List ── */
function TextbookList({ onSelect }: { onSelect: (id: string) => void }) {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const result = await listTextbooks({ page: p, page_size: 10 });
      if (p === 1) setTextbooks(result.items);
      else setTextbooks((prev) => [...prev, ...result.items]);
      setHasMore(result.items.length === 10 && (p * 10) < result.total);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(1); }, [load]);

  if (loading && page === 1) return <Loading />;
  if (textbooks.length === 0) return <Empty text="暂无教材" icon="📚" />;

  return (
    <div>
      {textbooks.map((tb) => (
        <div
          key={tb.id}
          className="card"
          onClick={() => onSelect(tb.id)}
          style={{ marginBottom: 'var(--spacing-md)', cursor: 'pointer' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
            <span style={{ fontSize: 36 }}>📗</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, marginBottom: 4 }}>{tb.title}</div>
              <div style={{ fontSize: 'var(--font-xs)', color: 'var(--color-text-tertiary)' }}>
                {tb.subject} · {tb.grade_range}
              </div>
            </div>
            <span style={{ color: 'var(--color-text-tertiary)' }}>→</span>
          </div>
        </div>
      ))}
      {hasMore && (
        <button
          className="btn btn-block"
          onClick={() => { setPage((p) => p + 1); load(page + 1); }}
          disabled={loading}
          style={{
            background: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-sm)',
          }}
        >
          {loading ? '加载中...' : '加载更多'}
        </button>
      )}
    </div>
  );
}

/* ── Task List ── */
function TaskList({ onSelect }: { onSelect: (id: string) => void }) {
  const [tasks, setTasks] = useState<LearningTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTasks()
      .then((r) => setTasks(r.items.filter((t: LearningTask) => t.status !== 'completed' && t.status !== 'expired')))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (tasks.length === 0) return <Empty text="暂无学习任务" icon="📝" />;

  return (
    <div>
      {tasks.map((task) => (
        <div
          key={task.id}
          className="card"
          onClick={() => onSelect(task.id)}
          style={{ marginBottom: 'var(--spacing-md)', cursor: 'pointer' }}
        >
          <div style={{ fontWeight: 500, marginBottom: 4 }}>{task.title}</div>
          <div style={{ fontSize: 'var(--font-xs)', color: 'var(--color-text-tertiary)' }}>
            进度 {task.progress_pct ?? 0}%
          </div>
        </div>
      ))}
    </div>
  );
}
