import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Form, Input, Switch, Select, Tag, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listSceneBindings,
  createSceneBinding,
  updateSceneBinding,
  deleteSceneBinding,
  listModelConfigs,
  type SceneModelBinding,
  type ModelConfig,
} from '@/api/model-config';

const SCENE_KEYS = [
  { value: 'tutor_chat', label: '智能辅导对话' },
  { value: 'exercise_gen', label: '练习题生成' },
  { value: 'content_summary', label: '内容摘要' },
  { value: 'knowledge_explain', label: '知识点讲解' },
  { value: 'homework_review', label: '作业批改' },
  { value: 'study_plan', label: '学习计划生成' },
];

export default function SceneBindingList() {
  const [data, setData] = useState<SceneModelBinding[]>([]);
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SceneModelBinding | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await listModelConfigs({ page: 1, size: 100 });
      setConfigs(res.items);
    } catch {
      // silent
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listSceneBindings({ page, size: pageSize });
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载场景绑定列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);
  useEffect(() => { fetchData(); }, [fetchData]);

  const configMap = new Map(configs.map((c) => [c.id, c]));

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const openEdit = (record: SceneModelBinding) => {
    setEditing(record);
    form.setFieldsValue({
      scene_key: record.scene_key,
      scene_label: record.scene_label || '',
      model_config_id: record.model_config_id,
      param_overrides: record.param_overrides ? JSON.stringify(record.param_overrides, null, 2) : '',
      is_active: record.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload: Record<string, unknown> = {
        scene_key: values.scene_key,
        scene_label: values.scene_label || undefined,
        model_config_id: values.model_config_id,
        is_active: values.is_active,
      };

      if (values.param_overrides) {
        try {
          payload.param_overrides = JSON.parse(values.param_overrides);
        } catch {
          message.error('参数覆盖 JSON 格式错误');
          setSubmitting(false);
          return;
        }
      }

      if (editing) {
        await updateSceneBinding(editing.scene_key, payload);
        message.success('更新成功');
      } else {
        await createSceneBinding(payload as Parameters<typeof createSceneBinding>[0]);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch {
      // validation or API error
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (sceneKey: string) => {
    try {
      await deleteSceneBinding(sceneKey);
      message.success('已删除');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const getSceneLabel = (key: string, label: string | null) => {
    if (label) return label;
    const s = SCENE_KEYS.find((sk) => sk.value === key);
    return s ? s.label : key;
  };

  const columns: ColumnsType<SceneModelBinding> = [
    {
      title: '场景',
      key: 'scene',
      width: 200,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{getSceneLabel(record.scene_key, record.scene_label)}</div>
          <code style={{ fontSize: 12, color: '#888' }}>{record.scene_key}</code>
        </div>
      ),
    },
    {
      title: '绑定模型',
      dataIndex: 'model_config_id',
      width: 220,
      render: (v: string) => {
        const c = configMap.get(v);
        return c ? (
          <div>
            <div>{c.display_name}</div>
            <code style={{ fontSize: 12, color: '#888' }}>{c.model_name}</code>
          </div>
        ) : <span style={{ color: '#999' }}>{v.slice(0, 8)}…</span>;
      },
    },
    {
      title: '参数覆盖',
      dataIndex: 'param_overrides',
      ellipsis: true,
      render: (v: Record<string, unknown>) => {
        if (!v || Object.keys(v).length === 0) return <span style={{ color: '#999' }}>-</span>;
        return <code>{JSON.stringify(v)}</code>;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此场景绑定？" onConfirm={() => handleDelete(record.scene_key)} okText="删除" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建场景绑定</Button>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
      />

      <Modal
        title={editing ? '编辑场景绑定' : '新建场景绑定'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="scene_key" label="场景标识" rules={[{ required: true, message: '请选择或输入场景标识' }]}>
            <Select
              showSearch
              placeholder="选择或输入场景标识"
              options={SCENE_KEYS}
              disabled={!!editing}
            />
          </Form.Item>
          <Form.Item name="scene_label" label="场景名称（可选）">
            <Input placeholder="自定义显示名称，留空使用默认" />
          </Form.Item>
          <Form.Item name="model_config_id" label="绑定模型" rules={[{ required: true, message: '请选择模型' }]}>
            <Select
              showSearch
              placeholder="选择模型配置"
              optionFilterProp="label"
              options={configs.filter((c) => c.is_active).map((c) => ({
                value: c.id,
                label: `${c.display_name} (${c.model_name})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="param_overrides" label="参数覆盖（JSON，可选）">
            <Input.TextArea rows={3} placeholder='{"temperature": 0.3}' />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
