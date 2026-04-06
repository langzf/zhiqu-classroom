import { useEffect, useState, useCallback } from 'react';
import {
  Table, Tag, Select, Space, Card, Typography, Button, Modal, Form,
  InputNumber, message,
} from 'antd';
import { EyeOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { GeneratedResource, KnowledgePoint } from '@zhiqu/shared';
import { listExercises, generateExercises, listKnowledgePoints } from '@/api/content';
import { EXERCISE_TYPE_LABELS } from '@zhiqu/shared';

const { Title } = Typography;

interface GenForm {
  knowledge_point_id: string;
  exercise_type: string;
  count: number;
  difficulty: number;
}

export default function ExerciseList() {
  const [data, setData] = useState<GeneratedResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState<unknown>(null);

  // Generate modal state
  const [genOpen, setGenOpen] = useState(false);
  const [genLoading, setGenLoading] = useState(false);
  const [kpList, setKpList] = useState<KnowledgePoint[]>([]);
  const [kpLoading, setKpLoading] = useState(false);
  const [genForm] = Form.useForm<GenForm>();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listExercises({ exercise_type: typeFilter });
      setData(res);
    } catch {
      // handled by global error handler
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load knowledge points for generate modal
  const loadKps = useCallback(async (subject?: string) => {
    setKpLoading(true);
    try {
      const res = await listKnowledgePoints({ subject, page: 1, page_size: 100 });
      setKpList(res.items ?? []);
    } catch {
      setKpList([]);
    } finally {
      setKpLoading(false);
    }
  }, []);

  // Load all KPs when generate modal opens
  useEffect(() => {
    if (genOpen) loadKps();
  }, [genOpen, loadKps]);

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

  const handleGenerate = async () => {
    try {
      const values = await genForm.validateFields();
      setGenLoading(true);
      await generateExercises(values);
      message.success('练习题生成成功');
      setGenOpen(false);
      genForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return; // form validation error
      message.error(err?.message || '生成失败，请重试');
    } finally {
      setGenLoading(false);
    }
  };

  const columns: ColumnsType<GeneratedResource> = [
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      width: 140,
      render: (t: string) => {
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
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => setGenOpen(true)}
          >
            生成练习题
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

      {/* Preview Modal */}
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

      {/* Generate Modal */}
      <Modal
        title="生成练习题"
        open={genOpen}
        onCancel={() => { setGenOpen(false); genForm.resetFields(); }}
        onOk={handleGenerate}
        confirmLoading={genLoading}
        okText="开始生成"
        cancelText="取消"
        width={520}
      >
        <Form
          form={genForm}
          layout="vertical"
          initialValues={{ exercise_type: 'choice', count: 5, difficulty: 3 }}
        >
          <Form.Item
            name="knowledge_point_id"
            label="选择知识点"
            rules={[{ required: true, message: '请选择知识点' }]}
          >
            <Select
              showSearch
              placeholder="选择或搜索知识点..."
              optionFilterProp="label"
              loading={kpLoading}
              notFoundContent={kpLoading ? '加载中...' : '暂无知识点'}
              options={kpList.map((kp) => ({
                value: kp.id,
                label: kp.title,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="exercise_type"
            label="题型"
            rules={[{ required: true }]}
          >
            <Select
              options={Object.entries(EXERCISE_TYPE_LABELS).map(([k, v]) => ({
                value: k,
                label: v,
              }))}
            />
          </Form.Item>

          <Space size="large">
            <Form.Item
              name="count"
              label="题目数量"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={20} />
            </Form.Item>

            <Form.Item
              name="difficulty"
              label="难度 (1-5)"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={5} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
