import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTask, listTaskItems } from '@/api/learning';
import { Loading, Empty } from '@/components/Feedback';
import type { LearningTask, TaskItem } from '@zhiqu/shared';
import { LEARNING_TASK_TYPE_LABELS, TASK_ITEM_STATUS_LABELS } from '@zhiqu/shared';

const STATUS_LABELS: Record<string, string> = {
  pending: '待完成',
  in_progress: '进行中',
  completed: '已完成',
  expired: '已过期',
};

const STATUS_COLORS: Record<string, string> = {
  pending: '#999',
  in_progress: 'var(--color-primary)',
  completed: '#10B981',
  expired: '#6B7280',
};

const ITEM_STATUS_COLORS: Record<string, string> = {
  pending: '#D1D5DB',
  in_progress: '#FBBF24',
  completed: '#10B981',
  skipped: '#9CA3AF',
};

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<LearningTask | null>(null);
  const [items, setItems] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const [taskData, itemsData] = await Promise.all([
          getTask(id),
          listTaskItems(id),
        ]);
        if (cancelled) return;
        setTask(taskData);
        setItems(itemsData);
      } catch {
        if (!cancelled) navigate('/study', { replace: true });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id, navigate]);

  if (loading) return <Loading />;
  if (!task) return <Empty text="任务不存在" icon="📋" />;

  const progressPct = Math.round(task.progress_pct * 100);
  const completedCount = items.filter((i) => i.status === 'completed').length;

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <button onClick={() => navigate(-1)} style={backBtnStyle}>
          ← 返回
        </button>
        <span style={headerTitleStyle}>任务详情</span>
        <div style={{ width: 60 }} />
      </div>

      {/* Content */}
      <div style={contentStyle}>
        {/* Task Info Card */}
        <div style={taskCardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: 0, marginBottom: 8 }}>
                {task.title}
              </h2>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ ...tagStyle, background: '#EEF2FF', color: 'var(--color-primary)' }}>
                  {LEARNING_TASK_TYPE_LABELS[task.task_type as keyof typeof LEARNING_TASK_TYPE_LABELS] ?? task.task_type}
                </span>
                <span style={{ ...tagStyle, background: '#F3F4F6', color: STATUS_COLORS[task.status] ?? '#999' }}>
                  {STATUS_LABELS[task.status] ?? task.status}
                </span>
              </div>
            </div>
          </div>

          {/* Progress */}
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 'var(--text-xs)', color: '#666' }}>
                进度 {completedCount}/{items.length}
              </span>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-primary)' }}>
                {progressPct}%
              </span>
            </div>
            <div style={progressBarBgStyle}>
              <div
                style={{
                  ...progressBarFillStyle,
                  width: `${progressPct}%`,
                }}
              />
            </div>
          </div>

          {task.completed_at && (
            <div style={{ marginTop: 12, fontSize: 'var(--text-xs)', color: '#999' }}>
              ✅ 完成于 {new Date(task.completed_at).toLocaleString('zh-CN')}
            </div>
          )}
        </div>

        {/* Task Items */}
        <div style={{ marginTop: 'var(--space-lg)' }}>
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 12 }}>
            任务项 ({items.length})
          </h3>
          {items.length === 0 ? (
            <Empty text="暂无任务项" icon="📝" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              {items.map((item, index) => (
                <div key={item.id} style={itemCardStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {/* Sequence number */}
                    <div style={{
                      ...seqBadgeStyle,
                      background: ITEM_STATUS_COLORS[item.status] ?? '#D1D5DB',
                    }}>
                      {index + 1}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                        第 {item.seq} 题
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: '#999', marginTop: 2 }}>
                        {TASK_ITEM_STATUS_LABELS[item.status] ?? item.status}
                        {item.score !== null && ` · ${item.score}分`}
                      </div>
                    </div>

                    {/* Status icon */}
                    <div style={{ fontSize: 20 }}>
                      {item.status === 'completed' ? '✅' :
                       item.status === 'in_progress' ? '✏️' :
                       item.status === 'skipped' ? '⏭️' : '⬜'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Component.displayName = 'TaskDetailPage';

/* ── Styles ── */

const pageStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  minHeight: '100vh',
  background: 'var(--color-bg)',
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  height: 56,
  padding: '0 var(--space-md)',
  background: '#fff',
  borderBottom: '1px solid var(--color-border-light)',
  flexShrink: 0,
};

const backBtnStyle: React.CSSProperties = {
  border: 'none',
  background: 'none',
  fontSize: 'var(--text-sm)',
  color: 'var(--color-primary)',
  cursor: 'pointer',
  padding: '4px 0',
  width: 60,
  textAlign: 'left',
};

const headerTitleStyle: React.CSSProperties = {
  fontSize: 'var(--text-base)',
  fontWeight: 600,
};

const contentStyle: React.CSSProperties = {
  flex: 1,
  padding: 'var(--space-md)',
  overflowY: 'auto',
};

const taskCardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-md)',
  boxShadow: 'var(--shadow-sm)',
};

const tagStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)',
  padding: '2px 8px',
  borderRadius: 'var(--radius-sm)',
  fontWeight: 500,
};

const progressBarBgStyle: React.CSSProperties = {
  height: 8,
  borderRadius: 4,
  background: '#F3F4F6',
  overflow: 'hidden',
};

const progressBarFillStyle: React.CSSProperties = {
  height: '100%',
  borderRadius: 4,
  background: 'linear-gradient(90deg, var(--color-primary), #818CF8)',
  transition: 'width 0.3s ease',
};

const itemCardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 'var(--radius-sm)',
  padding: '12px var(--space-md)',
  boxShadow: 'var(--shadow-sm)',
};

const seqBadgeStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 'var(--text-xs)',
  fontWeight: 700,
  color: '#fff',
  flexShrink: 0,
};
