import { useEffect, useState } from 'react';
import { Table, Tag, Select, Space, Card, Typography, Button, Modal } from 'antd';
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { GeneratedResource } from '@zhiqu/shared';
import { listExercises } from '@/api/content';
import { EXERCISE_TYPE_LABELS } from '@zhiqu/shared';

const { Title } = Typography;

export default function ExerciseList() {
  const [data, setData] = useState<GeneratedResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState<unknown>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await listExercises({ exercise_type: typeFilter });
      setData(res);
    } catch {
      // handled by global error handler
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [typeFilter]);

  const handlePreview = (record: GeneratedResource) => {
    try {
      setPreviewContent(
        typeof record.content_json === 'string'
          ? JSON.parse(record.content_json)
          : record.content_json,
      );
    } catch {
      setPreviewContent(record.content_json);
    }
    setPreviewOpen(true);
  };

  const columns: ColumnsType<GeneratedResource> = [
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      width: 140,
      render: (t: string) => {
        // resource_type is like "exercise_choice" → strip "exercise_" prefix for label lookup
        const key = t.replace('exercise_', '') as keyof typeof EXERCISE_TYPE_LABELS;
        return <Tag color="blue">{EXERCISE_TYPE_LABELS[key] ?? t}</Tag>;
      },
    },
    {
      title: '知识点 ID',
      dataIndex: 'knowledge_point_id',
      width: 280,
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作',
      width: 100,
      render: (_: unknown, record: GeneratedResource) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handlePreview(record)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <Card>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Title level={4} style={{ margin: 0 }}>练习题管理</Title>
        <Space>
          <Select
            allowClear
            placeholder="题型筛选"
            style={{ width: 160 }}
            value={typeFilter}
            onChange={setTypeFilter}
            options={Object.entries(EXERCISE_TYPE_LABELS).map(([k, v]) => ({
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
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
      <Modal
        title="练习题内容"
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={720}
      >
        <pre style={{ maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(previewContent, null, 2)}
        </pre>
      </Modal>
    </Card>
  );
}
