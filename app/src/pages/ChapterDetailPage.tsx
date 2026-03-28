import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { listKnowledgePoints, listKpResources } from '@/api/content';
import type { KnowledgePoint, GeneratedResource } from '@zhiqu/shared';
import './ChapterDetailPage.css';

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [kps, setKps] = useState<KnowledgePoint[]>([]);
  const [resources, setResources] = useState<Record<string, GeneratedResource[]>>({});
  const [expandedKp, setExpandedKp] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    listKnowledgePoints({ chapter_id: id, page: 1, page_size: 50 })
      .then((data) => setKps(data.items))
      .catch(() => navigate(-1))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  async function toggleKp(kpId: string) {
    if (expandedKp === kpId) {
      setExpandedKp(null);
      return;
    }
    setExpandedKp(kpId);
    if (!resources[kpId]) {
      try {
        const res = await listKpResources(kpId);
        setResources((prev) => ({ ...prev, [kpId]: res }));
      } catch {
        // ignore
      }
    }
  }

  if (loading) {
    return <div className="loading-center"><div className="spinner" /></div>;
  }

  return (
    <div className="chapter-detail-page page">
      <header className="ch-header">
        <button className="back-btn" onClick={() => navigate(-1)}>←</button>
        <h1>知识点列表</h1>
      </header>

      {kps.length === 0 ? (
        <div className="empty-state">暂无知识点</div>
      ) : (
        <div className="kp-accordion">
          {kps.map((kp) => (
            <div key={kp.id} className={`kp-card ${expandedKp === kp.id ? 'expanded' : ''}`}>
              <div className="kp-header" onClick={() => toggleKp(kp.id)}>
                <div className="kp-info">
                  <span className="kp-name">{kp.title}</span>
                  <span className="kp-meta">难度 {kp.difficulty ?? '-'}</span>
                </div>
                <span className="kp-toggle">{expandedKp === kp.id ? '▾' : '▸'}</span>
              </div>
              {expandedKp === kp.id && (
                <div className="kp-body">
                  {!resources[kp.id] ? (
                    <div className="loading-hint">加载中...</div>
                  ) : resources[kp.id].length === 0 ? (
                    <div className="empty-hint">暂无练习资源</div>
                  ) : (
                    <ul className="resource-list">
                      {resources[kp.id].map((r) => (
                        <li key={r.id} className="resource-item">
                          <span>{r.resource_type}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

Component.displayName = 'ChapterDetailPage';
