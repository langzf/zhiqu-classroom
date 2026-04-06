import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Form, Input, InputNumber, Switch, Select, message, Tag, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  type ModelProvider,
} from '@/api/model-config';

const PROVIDER_TYPES = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure_openai', label: 'Azure OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'google', label: 'Google (Gemini)' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'zhipu', label: '智谱 (ChatGLM)' },
  { value: 'moonshot', label: 'Moonshot (Kimi)' },
  { value: 'qwen', label: '通义千问' },
  { value: 'local', label: '本地部署' },
  { value: 'other', label: '其他' },
];

export default function ProviderList() {
  const [data, setData] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ModelProvider | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listProviders({ page, size: pageSize });
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载供应商列表失�?);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, sort_order: 0 });
    setModalOpen(true);
  };

  const openEdit = (record: ModelProvider) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      provider_type: record.provider_type,
      base_url: record.base_url || '',
      api_key: '', // don't prefill
      extra_config: record.extra_config ? JSON.stringify(record.extra_config, null, 2) : '',
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
        name: values.name,
        provider_type: values.provider_type,
        base_url: values.base_url || undefined,
        is_active: values.is_active,
        sort_order: values.sort_order ?? 0,
      };

      if (values.api_key) {
        payload.api_key = values.api_key;
      }

      if (values.extra_config) {
        try {
          payload.extra_config = JSON.parse(values.extra_config);
        } catch {
          message.error('扩展配置 JSON 格式错误');
          setSubmitting(false);
          return;
        }
      }

      if (editing) {
        // Remove unchanged fields for PATCH
        if (!values.api_key) delete payload.api_key;
        await updateProvider(editing.id, payload);
        message.success('更新成功');
      } else {
        if (!values.api_key) {
          message.error('新建供应商必须填�?API Key');
          setSubmitting(false);
          return;
        }
        await createProvider(payload as Parameters<typeof createProvider>[0]);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch {
      // validation error or API error
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProvider(id);
      message.success('已删�?);
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<ModelProvider> = [
    {
      title: '名称',
      dataIndex: 'name',
      width: 180,
    },
    {
      title: '类型',
      dataIndex: 'provider_type',
      width: 140,
      render: (v: string) => {
        const item = PROVIDER_TYPES.find((t) => t.value === v);
        return <Tag>{item ? item.label : v}</Tag>;
      },
    },
    {
      title: 'Base URL',
      dataIndex: 'base_url',
      ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>默认</span>,
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      width: 180,
      render: (v: string) => <Tooltip title={v}><code>{v}</code></Tooltip>,
    },
    {
      title: '状�?,
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
          <Popconfirm title="确认删除此供应商�? onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建供应�?/Button>
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
        title={editing ? '编辑供应�? : '新建供应�?}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入供应商名称' }]}>
            <Input placeholder="如：OpenAI 生产环境" />
          </Form.Item>
          <Form.Item name="provider_type" label="供应商类�? rules={[{ required: true, message: '请选择类型' }]}>
            <Select options={PROVIDER_TYPES} placeholder="选择供应商类�? />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL">
            <Input placeholder="留空使用默认地址，如 https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label={editing ? 'API Key（留空不修改�? : 'API Key'}
            rules={editing ? [] : [{ required: true, message: '请输�?API Key' }]}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item name="extra_config" label="扩展配置（JSON�?>
            <Input.TextArea rows={3} placeholder='{"org_id": "xxx"}' />
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
