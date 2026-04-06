import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { sendCode, loginByPhone } from '@/api/user';
import { useAuthStore } from '@/stores/authStore';

export function Component() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendCode = useCallback(async () => {
    if (!phone || phone.length !== 11) {
      setError('请输入正确的手机号');
      return;
    }
    try {
      await sendCode(phone);
      setCodeSent(true);
      setCountdown(60);
      setError('');
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch {
      setError('发送验证码失败');
    }
  }, [phone]);

  const handleLogin = useCallback(async () => {
    if (!phone || phone.length !== 11) {
      setError('请输入正确的手机号');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await loginByPhone(phone, code || '000000');
      setAuth(data);
      navigate('/', { replace: true });
    } catch {
      setError('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [phone, code, setAuth, navigate]);

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>📖 智趣课堂</h1>
        <p style={subtitleStyle}>AI 智能学习助手</p>

        <div style={formStyle}>
          <input
            type="tel"
            placeholder="请输入手机号"
            value={phone}
            maxLength={11}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
            style={inputStyle}
          />

          <div style={codeRowStyle}>
            <input
              type="text"
              placeholder="验证码 (MVP可跳过)"
              value={code}
              maxLength={6}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              style={{ ...inputStyle, flex: 1 }}
            />
            <button
              onClick={handleSendCode}
              disabled={countdown > 0}
              style={{
                ...sendBtnStyle,
                opacity: countdown > 0 ? 0.5 : 1,
              }}
            >
              {countdown > 0 ? `${countdown}s` : codeSent ? '重发' : '获取验证码'}
            </button>
          </div>

          {error && <p style={errorStyle}>{error}</p>}

          <button
            onClick={handleLogin}
            disabled={loading || !phone}
            style={{
              ...loginBtnStyle,
              opacity: loading || !phone ? 0.6 : 1,
            }}
          >
            {loading ? '登录中...' : '登录 / 注册'}
          </button>

          <p style={tipStyle}>未注册手机号将自动创建账号</p>
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  padding: 'var(--spacing-md)',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 'var(--radius-lg)',
  padding: '40px var(--spacing-lg)',
  width: '100%',
  maxWidth: 400,
  boxShadow: 'var(--shadow-md)',
  textAlign: 'center',
};

const titleStyle: React.CSSProperties = {
  fontSize: '28px',
  fontWeight: 700,
  margin: 0,
  color: '#333',
};

const subtitleStyle: React.CSSProperties = {
  fontSize: 'var(--font-sm)',
  color: '#999',
  margin: '8px 0 32px',
};

const formStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--spacing-md)',
};

const inputStyle: React.CSSProperties = {
  height: 48,
  borderRadius: 'var(--radius-sm)',
  border: '1px solid #ddd',
  padding: '0 var(--spacing-md)',
  fontSize: 'var(--font-md)',
  outline: 'none',
  transition: 'border-color .2s',
};

const codeRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: 'var(--spacing-sm)',
};

const sendBtnStyle: React.CSSProperties = {
  flexShrink: 0,
  height: 48,
  padding: '0 var(--spacing-md)',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--color-primary)',
  background: 'transparent',
  color: 'var(--color-primary)',
  fontSize: 'var(--font-sm)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

const loginBtnStyle: React.CSSProperties = {
  height: 48,
  borderRadius: 'var(--radius-sm)',
  border: 'none',
  background: 'var(--color-primary)',
  color: '#fff',
  fontSize: 'var(--font-md)',
  fontWeight: 600,
  cursor: 'pointer',
};

const errorStyle: React.CSSProperties = {
  color: '#ef4444',
  fontSize: 'var(--font-sm)',
  margin: 0,
};

const tipStyle: React.CSSProperties = {
  fontSize: 'var(--font-xs)',
  color: '#bbb',
  margin: 0,
};
