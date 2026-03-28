import { useEffect, useState } from 'react';
import { Table, Tag, Card, Typography, Space, Button, Select } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { LearningTask } from '@/api/learning';
import { TASK_STATUS_LABELS } from '@zhiqu/shared';
import { listTasks } from '@/api/learning';

const { Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  expired: 'error',
};

export default function TaskList() {
  const [tasks, setTasks] = useState<LearningTask[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await listTasks({ page, page_size: pageSize, status: statusFilter });
      setTasks(res.items);
      setTotal(res.total);
    } catch {
      // handled by global error handler
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, pageSize, statusFilter]);

  const columns: ColumnsType<LearningTask> = [
    {
      title: '任务标题',
      dataIndex: 'title',
      ellipsis: true,
    },
    {
      title: '学生 ID',
      dataIndex: 'student_id',
      width: 280,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] ?? 'default'}>
          {TASK_STATUS_LABELS[s as keyof typeof TASK_STATUS_LABELS] ?? s}
        </Tag>
      ),
    },
    {
      title: '截止时间',
      dataIndex: 'due_date',
      width: 180,
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
  ];

  return (
    <Card>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Title level={4} style={{ margin: 0 }}>学习任务</Title>
        <Space>
          <Select
            allowClear
            placeholder="状态筛选"
            style={{ width: 140 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={Object.entries(TASK_STATUS_LABELS).map(([k, v]) => ({
              value: k,
              label: v,
            }))}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            刷新
          </Button>
        </Space>
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={tasks}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, s) => {
            setPage(p);
            setPageSize(s);
          },
        }}
      />
    </Card>
  );
}
