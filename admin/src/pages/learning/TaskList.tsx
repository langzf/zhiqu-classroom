import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Typography, Tag, message, Space, Select } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listTasks } from '@/api/learning';
import type { LearningTask } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  expired: 'error',
};
const statusLabels: Record<string, string> = {
  pending: '待开始',
  in_progress: '进行中',
  completed: '已完成',
  expired: '已过期',
};

const taskTypeLabels: Record<string, string> = {
  exercise: '练习',
  reading: '阅读',
  review: '复习',
  quiz: '测验',
};

export default function TaskList() {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<LearningTask[]>([]);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTasks({ status: statusFilter, limit: 50 });
      setTasks(data);
    } catch {
      message.error('加载学习任务失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns: ColumnsType<LearningTask> = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 100,
      render: (v: string) => <Tag>{taskTypeLabels[v] || v}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => (
        <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: '截止时间',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 170,
      render: (v: string) => v ? formatDate(v) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string) => formatDate(v),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>学习任务</Title>
        <Space>
          <Select
            allowClear
            placeholder="筛选状态"
            style={{ width: 120 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={tasks}
        columns={columns}
        pagination={{ pageSize: 20 }}
      />
    </div>
  );
}
