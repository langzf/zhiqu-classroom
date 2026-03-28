import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';

export function Component() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
      {/* Avatar & Name */}
      <div
        style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          padding: 'var(--spacing-2xl) 0',
        }}
      >
        <div
          style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'var(--color-primary-bg)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 32,
            marginBottom: 'var(--spacing-md)',
          }}
        >
          👤
        </div>
        <div style={{ fontSize: 'var(--font-xl)', fontWeight: 600 }}>
          {user?.nickname || '未设置昵称'}
        </div>
        <div style={{ fontSize: 'var(--font-sm)', color: 'var(--color-text-tertiary)', marginTop: 4 }}>
          {user?.phone || ''}
        </div>
      </div>

      {/* Menu */}
      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        {[
          { icon: '📊', label: '学习统计', onClick: () => {} },
          { icon: '⭐', label: '我的收藏', onClick: () => {} },
          { icon: '📝', label: '错题本', onClick: () => {} },
        ].map((item) => (
          <div
            key={item.label}
            onClick={item.onClick}
            style={{
              display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)',
              padding: 'var(--spacing-md) 0',
              borderBottom: '1px solid var(--color-border-light)',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 20 }}>{item.icon}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>→</span>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        {[
          { icon: '⚙️', label: '设置', onClick: () => {} },
          { icon: '❓', label: '帮助与反馈', onClick: () => {} },
          { icon: '📄', label: '关于', onClick: () => {} },
        ].map((item) => (
          <div
            key={item.label}
            onClick={item.onClick}
            style={{
              display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)',
              padding: 'var(--spacing-md) 0',
              borderBottom: '1px solid var(--color-border-light)',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 20 }}>{item.icon}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>→</span>
          </div>
        ))}
      </div>

      <button
        className="btn btn-block"
        onClick={handleLogout}
        style={{
          height: 48, background: 'var(--color-bg-white)',
          color: 'var(--color-danger)', border: '1px solid var(--color-border)',
          fontSize: 'var(--font-md)',
        }}
      >
        退出登录
      </button>
    </div>
  );
}

Component.displayName = 'ProfilePage';
