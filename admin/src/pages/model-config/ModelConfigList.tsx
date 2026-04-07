import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Form, Input, InputNumber, Switch, Select, Tag, message, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listModelConfigs,
  createModelConfig,
  updateModelConfig,
  deleteModelConfig,
  listProviders,
  type ModelConfig,
  type ModelProvider,
} from '@/api/model-config';

const CAPABILITIES = [
  { value: 'chat', label: '对话 (chat)' },
  { value: 'completion', label: '补全 (completion)' },
  { value: 'embedding', label: '向量化 (embedding)' },
  { value: 'vision', label: '多模态 (vision)' },
  { value: 'function_calling', label: '工具调用 (function_calling)' },
  { value: 'json_mode', label: 'JSON 模式' },
];

export default function ModelConfigList() {
  const [data, setData] = useState<ModelConfig[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterProvider, setFilterProvider] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfig | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchProviders = useCallback(async () => {
    try {
      const res = await listProviders({ page: 1, size: 100 });
      setProviders(res.items);
    } catch {
      // silent
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listModelConfigs({ provider_id: filterProvider, page, size: pageSize });
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载模型配置列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterProvider]);

  useEffect(() => { fetchProviders(); }, [fetchProviders]);
  useEffect(() => { fetchData(); }, [fetchData]);

  const providerMap = new Map(providers.map((p) => [p.id, p]));

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, sort_order: 0, capabilities: ['chat'] });
    setModalOpen(true);
  };

  const openEdit = (record: ModelConfig) => {
    setEditing(record);
    form.setFieldsValue({
      provider_id: record.provider_id,
      model_name: record.model_name,
      display_name: record.display_name,
      capabilities: record.capabilities,
      default_params: record.default_params ? JSON.stringify(record.default_params, null, 2) : '',
      is_active: record.is_active,
      sort_order: record.sort_order,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload: Record<string, unknown> = {
        provider_id: values.provider_id,
        model_name: values.model_name,
        display_name: values.display_name,
        capabilities: values.capabilities || [],
        is_active: values.is_active,
        sort_order: values.sort_order ?? 0,
      };

      if (values.default_params) {
        try {
          payload.default_params = JSON.parse(values.default_params);
        } catch {
          message.error('默认参数 JSON 格式错误');
          setSubmitting(false);
          return;
        }
      }

      if (editing) {
        await updateModelConfig(editing.id, payload);
        message.success('更新成功');
      } else {
        await createModelConfig(payload as Parameters<typeof createModelConfig>[0]);
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

  const handleDelete = async (id: string) => {
    try {
      await deleteModelConfig(id);
      message.success('已删除');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<ModelConfig> = [
    {
      title: '显示名称',
      dataIndex: 'display_name',
      width: 200,
    },
    {
      title: '模型名',
      dataIndex: 'model_name',
      width: 200,
      render: (v: string) => <code>{v}</code>,
    },
    {
      title: '供应商',
      dataIndex: 'provider_id',
      width: 160,
      render: (v: string) => {
        const p = providerMap.get(v);
        return p ? p.name : <span style={{ color: '#999' }}>{v.slice(0, 8)}…</span>;
      },
    },
    {
      title: '能力',
      dataIndex: 'capabilities',
      render: (caps: string[]) => (
        <Space size={[0, 4]} wrap>
          {caps.map((c) => <Tag key={c} color="blue">{c}</Tag>)}
        </Space>
      ),
    },
    {
      title: '默认参数',
      dataIndex: 'default_params',
      ellipsis: true,
      width: 180,
      render: (v: Record<string, unknown>) => {
        if (!v || Object.keys(v).length === 0) return <span style={{ color: '#999' }}>-</span>;
        const text = JSON.stringify(v);
        return <Tooltip title={<pre style={{ margin: 0, maxWidth: 400, whiteSpace: 'pre-wrap' }}>{JSON.stringify(v, null, 2)}</pre>}><code>{text.length > 40 ? text.slice(0, 40) + '…' : text}</code></Tooltip>;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      width: 70,
    },
    {
      title: '操作',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此模型配置？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建模型配置</Button>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        <Select
          allowClear
          placeholder="按供应商筛选"
          style={{ width: 200 }}
          value={filterProvider}
          onChange={(v) => { setFilterProvider(v); setPage(1); }}
          options={providers.map((p) => ({ value: p.id, label: p.name }))}
        />
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
        title={editing ? '编辑模型配置' : '新建模型配置'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="provider_id" label="供应商" rules={[{ required: true, message: '请选择供应商' }]}>
            <Select
              placeholder="选择供应商"
              options={providers.filter((p) => p.is_active).map((p) => ({ value: p.id, label: p.name }))}
            />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true, message: '请输入模型名称' }]}>
            <Input placeholder="如 gpt-4o, claude-3.5-sonnet" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 GPT-4o（主力）" />
          </Form.Item>
          <Form.Item name="capabilities" label="能力标签">
            <Select mode="multiple" placeholder="选择模型能力" options={CAPABILITIES} />
          </Form.Item>
          <Form.Item name="default_params" label="默认参数（JSON）">
            <Input.TextArea rows={3} placeholder='{"temperature": 0.7, "max_tokens": 2048}' />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
