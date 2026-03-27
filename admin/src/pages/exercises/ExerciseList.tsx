import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Space, Typography, Tag, Select, InputNumber,
  Modal, Form, Input, message, Card, Row, Col, Descriptions, Collapse,
} from 'antd';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listExercises, generateExercises, searchKnowledgePoints } from '@/api/content';
import type { GeneratedResource, KnowledgePoint } from '@zhiqu/shared';
import { EXERCISE_TYPE_LABELS } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';

const { Title, Text } = Typography;

const typeColors: Record<string, string> = {
  exercise_choice: 'blue',
  exercise_fill_blank: 'green',
  exercise_short_answer: 'orange',
  exercise_true_false: 'purple',
};

interface Question {
  id: string;
  stem: string;
  options?: string[];
  answer: string;
  explanation?: string;
  difficulty?: number;
}

export default function ExerciseList() {
  const [loading, setLoading] = useState(false);
  const [exercises, setExercises] = useState<GeneratedResource[]>([]);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<GeneratedResource | null>(null);
  const [kpResults, setKpResults] = useState<KnowledgePoint[]>([]);
  const [kpSearching, setKpSearching] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listExercises({
        exercise_type: typeFilter,
        limit: 50,
      });
      setExercises(data);
    } catch {
      message.error('加载练习题失败');
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleGenerate = async (values: {
    knowledge_point_id: string;
    exercise_type: string;
    count: number;
    difficulty: number;
  }) => {
    setGenerating(true);
    try {
      await generateExercises(values);
      message.success('练习题生成成功');
      setGenerateOpen(false);
      form.resetFields();
      fetchData();
    } catch {
      message.error('生成失败，请重试');
    } finally {
      setGenerating(false);
    }
  };

  const handleKpSearch = async (query: string) => {
    if (!query || query.length < 2) { setKpResults([]); return; }
    setKpSearching(true);
    try {
      const data = await searchKnowledgePoints({ query, limit: 10 });
      setKpResults(data);
    } catch { /* ignore */ } finally {
      setKpSearching(false);
    }
  };

  const handlePreview = (record: GeneratedResource) => {
    setPreviewData(record);
    setPreviewOpen(true);
  };

  const columns: ColumnsType<GeneratedResource> = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '题型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 120,
      render: (v: string) => (
        <Tag color={typeColors[v] || 'default'}>
          {EXERCISE_TYPE_LABELS[v] || v}
        </Tag>
      ),
    },
    {
      title: '题目数量',
      key: 'question_count',
      width: 100,
      render: (_: unknown, record: GeneratedResource) => {
        const content = record.content_json as { questions?: Question[] };
        return content?.questions?.length ?? '-';
      },
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 100,
      render: (v: number | null) => v != null ? `${v}/10` : '-',
    },
    {
      title: '模型',
      dataIndex: 'llm_model',
      key: 'llm_model',
      width: 140,
      ellipsis: true,
    },
    {
      title: '生成时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string) => formatDate(v),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: GeneratedResource) => (
        <Button type="link" onClick={() => handlePreview(record)}>查看</Button>
      ),
    },
  ];

  const typeOptions = Object.entries(EXERCISE_TYPE_LABELS).map(([k, v]) => ({
    value: k.replace('exercise_', ''),
    label: v,
  }));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>练习题管理</Title>
        <Space>
          <Select
            allowClear
            placeholder="筛选题型"
            style={{ width: 140 }}
            options={typeOptions.map(o => ({ ...o, value: `exercise_${o.value}` }))}
            onChange={setTypeFilter}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setGenerateOpen(true)}>
            生成练习题
          </Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={exercises}
        columns={columns}
        pagination={{ pageSize: 20 }}
      />

      {/* Generate Modal */}
      <Modal
        title="AI 生成练习题"
        open={generateOpen}
        onCancel={() => setGenerateOpen(false)}
        footer={null}
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ exercise_type: 'choice', count: 5, difficulty: 3 }}
          onFinish={handleGenerate}
        >
          <Form.Item
            name="knowledge_point_id"
            label="知识点"
            rules={[{ required: true, message: '请选择知识点' }]}
          >
            <Select
              showSearch
              placeholder="搜索知识点..."
              filterOption={false}
              onSearch={handleKpSearch}
              loading={kpSearching}
              suffixIcon={<SearchOutlined />}
              options={kpResults.map(kp => ({
                value: kp.id,
                label: `${kp.name}`,
              }))}
              notFoundContent={kpSearching ? '搜索中...' : '输入关键词搜索'}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="exercise_type" label="题型" rules={[{ required: true }]}>
                <Select options={typeOptions} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="count" label="数量">
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="difficulty" label="难度 (1-5)">
                <InputNumber min={1} max={5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={generating} block>
              开始生成
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title="练习题详情"
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={<Button onClick={() => setPreviewOpen(false)}>关闭</Button>}
        width={700}
      >
        {previewData && (
          <>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="标题">{previewData.title}</Descriptions.Item>
              <Descriptions.Item label="题型">
                <Tag color={typeColors[previewData.resource_type]}>
                  {EXERCISE_TYPE_LABELS[previewData.resource_type] || previewData.resource_type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型">{previewData.llm_model}</Descriptions.Item>
              <Descriptions.Item label="质量评分">
                {previewData.quality_score != null ? `${previewData.quality_score}/10` : '-'}
              </Descriptions.Item>
            </Descriptions>

            <Collapse
              defaultActiveKey={
                ((previewData.content_json as { questions?: Question[] })?.questions ?? [])
                  .map((_: unknown, i: number) => String(i))
              }
              items={
                ((previewData.content_json as { questions?: Question[] })?.questions ?? [])
                  .map((q: Question, i: number) => ({
                    key: String(i),
                    label: (
                      <Space>
                        <Tag>{`Q${i + 1}`}</Tag>
                        <Text>{q.stem}</Text>
                      </Space>
                    ),
                    children: (
                      <Card size="small" bordered={false}>
                        {q.options && q.options.length > 0 && (
                          <div style={{ marginBottom: 8 }}>
                            <Text strong>选项：</Text>
                            <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                              {q.options.map((opt: string, j: number) => (
                                <li key={j}>{opt}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div style={{ marginBottom: 4 }}>
                          <Text strong>答案：</Text>
                          <Text type="success">{q.answer}</Text>
                        </div>
                        {q.explanation && (
                          <div>
                            <Text strong>解析：</Text>
                            <Text type="secondary">{q.explanation}</Text>
                          </div>
                        )}
                      </Card>
                    ),
                  }))
              }
            />
          </>
        )}
      </Modal>
    </div>
  );
}
