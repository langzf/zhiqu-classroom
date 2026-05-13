import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import { getVoiceSetting, listVoiceProfiles, updateVoiceSetting } from '@/api/voice';
import type { VoiceProfile, VoiceSetting } from '@zhiqu/shared';

export function Component() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [voiceSetting, setVoiceSetting] = useState<VoiceSetting | null>(null);
  const [savingVoice, setSavingVoice] = useState(false);

  useEffect(() => {
    let mounted = true;
    Promise.all([listVoiceProfiles(), getVoiceSetting()])
      .then(([profiles, setting]) => {
        if (!mounted) return;
        setVoiceProfiles(profiles);
        setVoiceSetting(setting);
      })
      .catch(() => {
        if (mounted) {
          setVoiceProfiles([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const saveVoiceSetting = async (next: {
    voice_profile_id?: string | null;
    auto_play?: boolean;
  }) => {
    setSavingVoice(true);
    try {
      const updated = await updateVoiceSetting({
        voice_profile_id: next.voice_profile_id ?? voiceSetting?.voice_profile_id ?? null,
        auto_play: next.auto_play ?? voiceSetting?.auto_play ?? false,
      });
      setVoiceSetting(updated);
    } finally {
      setSavingVoice(false);
    }
  };

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
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
            alignItems: 'center', justifyContent: 'center', fontSize: 28,
            marginBottom: 'var(--spacing-md)',
          }}
        >
          用户
        </div>
        <div style={{ fontSize: 'var(--font-xl)', fontWeight: 600 }}>
          {user?.nickname || '未设置昵称'}
        </div>
        <div style={{ fontSize: 'var(--font-sm)', color: 'var(--color-text-tertiary)', marginTop: 4 }}>
          {user?.phone || ''}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <div style={{ fontWeight: 600, marginBottom: 'var(--spacing-md)' }}>语音设置</div>
        <label style={{ display: 'block', fontSize: 'var(--font-sm)', color: 'var(--color-text-secondary)', marginBottom: 6 }}>
          助教播报音色
        </label>
        <select
          value={voiceSetting?.voice_profile_id || ''}
          disabled={savingVoice}
          onChange={(event) => saveVoiceSetting({ voice_profile_id: event.target.value || null })}
          style={{
            width: '100%',
            height: 42,
            borderRadius: 8,
            border: '1px solid var(--color-border)',
            padding: '0 12px',
            background: 'var(--color-bg-white)',
            marginBottom: 'var(--spacing-md)',
          }}
        >
          <option value="">默认音色</option>
          {voiceProfiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="checkbox"
            checked={voiceSetting?.auto_play || false}
            disabled={savingVoice}
            onChange={(event) => saveVoiceSetting({ auto_play: event.target.checked })}
          />
          <span>聊天回复后自动播放语音</span>
        </label>
      </div>

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
            <span style={{ color: 'var(--color-text-tertiary)' }}>›</span>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        {[
          { icon: '⚙️', label: '设置', onClick: () => {} },
          { icon: '♥', label: '帮助与反馈', onClick: () => {} },
          { icon: '📌', label: '关于', onClick: () => {} },
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
            <span style={{ color: 'var(--color-text-tertiary)' }}>›</span>
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
