import React, { useState } from 'react';
import { Button, Card, Form, Input, message, Typography } from 'antd';
import { MobileOutlined, SafetyOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { loginByPhone, sendCode } from '@/api/user';
import { useAuthStore } from '@/stores/authStore';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [codeSending, setCodeSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const handleSendCode = async () => {
    const phone = form.getFieldValue('phone');
    if (!phone || phone.length !== 11) {
      message.warning('请输入正确的手机号');
      return;
    }
    setCodeSending(true);
    try {
      await sendCode(phone);
      message.success('验证码已发送');
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err: any) {
      message.error(err.message || '发送失败');
    } finally {
      setCodeSending(false);
    }
  };

  const handleLogin = async (values: { phone: string; code?: string }) => {
    setLoading(true);
    try {
      const data = await loginByPhone(values.phone, values.code);
      setAuth(data.access_token, data.refresh_token!, data.user!);
      message.success('登录成功');
      navigate(from, { replace: true });
    } catch (err: any) {
      message.error(err.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card style={{ width: 400, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={3} style={{ marginBottom: 4 }}>知趣课堂</Title>
          <Text type="secondary">管理后台</Text>
        </div>

        <Form form={form} onFinish={handleLogin} layout="vertical" size="large">
          <Form.Item
            name="phone"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
            ]}
          >
            <Input prefix={<MobileOutlined />} placeholder="手机号" maxLength={11} />
          </Form.Item>

          <Form.Item name="code">
            <Input
              prefix={<SafetyOutlined />}
              placeholder="验证码（MVP 可留空）"
              maxLength={6}
              suffix={
                <Button
                  type="link"
                  size="small"
                  disabled={countdown > 0}
                  loading={codeSending}
                  onClick={handleSendCode}
                  style={{ padding: 0 }}
                >
                  {countdown > 0 ? `${countdown}s` : '获取验证码'}
                </Button>
              }
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default LoginPage;
