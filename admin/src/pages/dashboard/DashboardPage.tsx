import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Spin } from 'antd';
import {
  BookOutlined,
  UserOutlined,
  MessageOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { listTextbooks } from '@/api/content';
import { listUsers } from '@/api/user';
import { listConversations } from '@/api/tutor';
import { listTasks } from '@/api/learning';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    textbooks: 0,
    users: 0,
    conversations: 0,
    tasks: 0,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        const [tb, usr, conv, task] = await Promise.all([
          listTextbooks({ page: 1, page_size: 1 }),
          listUsers({ page: 1, page_size: 1 }),
          listConversations({ page: 1, page_size: 1 }),
          listTasks({ page: 1, page_size: 1 }),
        ]);
        setStats({
          textbooks: tb.total,
          users: usr.total,
          conversations: conv.total,
          tasks: task.total,
        });
      } catch {
        // silently ignore — dashboard stats are non-critical
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  return (
    <Spin spinning={loading}>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="教材总数"
              value={stats.textbooks}
              prefix={<BookOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="用户总数"
              value={stats.users}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="对话总数"
              value={stats.conversations}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="学习任务"
              value={stats.tasks}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  );
}
