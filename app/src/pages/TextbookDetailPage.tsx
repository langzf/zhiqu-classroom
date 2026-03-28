import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTextbook, listChapters, listKnowledgePoints } from '@/api/content';
import type { Textbook, Chapter, KnowledgePoint } from '@zhiqu/shared';
import { SUBJECT_LABELS } from '@zhiqu/shared';
import './TextbookDetailPage.css';

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [textbook, setTextbook] = useState<Textbook | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [kps, setKps] = useState<KnowledgePoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      getTextbook(id),
      listChapters(id),
    ])
      .then(([tb, chs]) => {
        setTextbook(tb);
        setChapters(chs);
      })
      .catch(() => navigate('/study', { replace: true }))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  // load knowledge points for first chapter
  useEffect(() => {
    if (chapters.length === 0) return;
    listKnowledgePoints({ chapter_id: chapters[0].id, page: 1, page_size: 50 })
      .then((data) => setKps(data.items))
      .catch(() => {});
  }, [chapters]);

  if (loading) {
    return <div className="loading-center"><div className="spinner" /></div>;
  }

  if (!textbook) {
    return <div className="empty-state">教材不存在</div>;
  }

  return (
    <div className="tb-detail-page page">
      <header className="tb-detail-header">
        <button className="back-btn" onClick={() => navigate('/study')}>←</button>
        <h1>{textbook.title}</h1>
      </header>

      <div className="tb-info">
        <span className="info-tag">{SUBJECT_LABELS[textbook.subject as keyof typeof SUBJECT_LABELS] ?? textbook.subject}</span>
        <span className="info-tag">{textbook.grade_range}</span>
      </div>

      <section className="tb-section">
        <h2>📖 章节 ({chapters.length})</h2>
        {chapters.length === 0 ? (
          <p className="empty-hint">暂无章节</p>
        ) : (
          <div className="chapter-list">
            {chapters.map((ch) => (
              <div
                key={ch.id}
                className="chapter-item"
                onClick={() => navigate(`/chapters/${ch.id}`)}
              >
                <span className="chapter-title">{ch.title}</span>
                <span className="chapter-arrow">›</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {kps.length > 0 && (
        <section className="tb-section">
          <h2>💡 知识点</h2>
          <div className="kp-list">
            {kps.map((kp) => (
              <div key={kp.id} className="kp-item">
                <span className="kp-name">{kp.title}</span>
                <span className="kp-difficulty">难度 {kp.difficulty ?? '-'}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

Component.displayName = 'TextbookDetailPage';
