import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listTextbooks } from '@/api/content';
import { listTasks } from '@/api/learning';
import type { Textbook, LearningTask } from '@zhiqu/shared';
import './HomePage.css';

export function Component() {
  const navigate = useNavigate();
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [tasks, setTasks] = useState<LearningTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listTextbooks({ page: 1, page_size: 4 }),
      listTasks({ page: 1, page_size: 5 }),
    ])
      .then(([tbData, taskData]) => {
        setTextbooks(tbData.items);
        setTasks(taskData.items.filter((t) => t.status !== 'archived'));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="loading-center"><div className="spinner" /></div>;
  }

  return (
    <div className="home-page page">
      <section className="home-section">
        <div className="section-header">
          <h2>📚 我的教材</h2>
          <button className="link-btn" onClick={() => navigate('/study')}>查看全部</button>
        </div>
        {textbooks.length === 0 ? (
          <p className="empty-hint">暂无教材</p>
        ) : (
          <div className="card-grid">
            {textbooks.map((tb) => (
              <div key={tb.id} className="card" onClick={() => navigate(`/textbooks/${tb.id}`)}>
                <div className="card-title">{tb.title}</div>
                <div className="card-meta">{tb.subject} · {tb.grade_range}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="home-section">
        <div className="section-header">
          <h2>📝 学习任务</h2>
          <button className="link-btn" onClick={() => navigate('/study')}>查看全部</button>
        </div>
        {tasks.length === 0 ? (
          <p className="empty-hint">暂无任务</p>
        ) : (
          <div className="task-list">
            {tasks.map((task) => (
              <div key={task.id} className="task-card" onClick={() => navigate(`/tasks/${task.id}`)}>
                <div className="task-title">{task.title}</div>
                <div className="task-meta">
                  <span className={`status-tag ${task.status}`}>{task.status}</span>
                  {task.progress_pct != null && (
                    <span className="progress-text">{Math.round(task.progress_pct)}%</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

Component.displayName = 'HomePage';
