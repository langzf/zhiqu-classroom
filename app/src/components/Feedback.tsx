export function Loading({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="loading-center">
      <div className="spinner" />
      <span style={{ marginLeft: 8, color: 'var(--color-text-secondary)', fontSize: 14 }}>
        {text}
      </span>
    </div>
  );
}

export function Empty({ text = '暂无数据', icon = '📭' }: { text?: string; icon?: string }) {
  return (
    <div className="empty-state">
      <span className="icon">{icon}</span>
      <span>{text}</span>
    </div>
  );
}
