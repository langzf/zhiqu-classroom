import { NavLink, Outlet } from 'react-router-dom';

const tabs = [
  { to: '/', label: '首页', icon: '🏠' },
  { to: '/study', label: '学习', icon: '📚' },
  { to: '/chat', label: 'AI辅导', icon: '💬' },
  { to: '/profile', label: '我的', icon: '👤' },
];

const layoutStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100vh',
  background: 'var(--color-bg)',
};

const bodyStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
};

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  borderTop: '1px solid #e5e5e5',
  background: '#fff',
  paddingBottom: 'env(safe-area-inset-bottom)',
};

const tabStyle: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '6px 0',
  fontSize: 'var(--text-xs)',
  color: '#999',
  textDecoration: 'none',
  transition: 'color .2s',
};

const activeTabStyle: React.CSSProperties = {
  ...tabStyle,
  color: 'var(--color-primary)',
};

export function MainLayout() {
  return (
    <div style={layoutStyle}>
      <div style={bodyStyle}>
        <Outlet />
      </div>
      <nav style={tabBarStyle}>
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/'}
            style={({ isActive }) => (isActive ? activeTabStyle : tabStyle)}
          >
            <span style={{ fontSize: '20px' }}>{tab.icon}</span>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
