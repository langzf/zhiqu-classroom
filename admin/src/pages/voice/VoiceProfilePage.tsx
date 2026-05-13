import { useEffect, useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tag, Upload, message } from 'antd';
import { PlusOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';
import type { VoiceProfile } from '@zhiqu/shared';
import { createVoiceProfile, listVoiceProfiles } from '@/api/voice';

export default function VoiceProfilePage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const normalizeUpload = (event: { fileList?: UploadFile[] } | UploadFile[]) => (
    Array.isArray(event) ? event : event?.fileList || []
  );

  const fetchProfiles = async () => {
    setLoading(true);
    try {
      setProfiles(await listVoiceProfiles(true));
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    provider: 'tts' | 'openvoice';
    voice_key?: string;
    is_active: boolean;
    sort_order: number;
    file?: UploadFile[];
  }) => {
    try {
      await createVoiceProfile({
        name: values.name,
        description: values.description,
        provider: values.provider,
        voice_key: values.voice_key,
        is_active: values.is_active,
        sort_order: values.sort_order || 0,
        file: values.file?.[0]?.originFileObj,
      });
      message.success('音色已保存');
      setOpen(false);
      form.resetFields();
      fetchProfiles();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    }
  };

  const columns: ColumnsType<VoiceProfile> = [
    { title: '名称', dataIndex: 'name' },
    {
      title: '类型',
      dataIndex: 'provider',
      width: 120,
      render: (v) => <Tag color={v === 'openvoice' ? 'purple' : 'blue'}>{v === 'openvoice' ? '克隆音色' : '普通TTS'}</Tag>,
    },
    { title: 'Voice', dataIndex: 'voice_key', width: 140 },
    {
      title: '参考音频',
      dataIndex: 'has_reference_audio',
      width: 100,
      render: (v) => (v ? <Tag color="green">已上传</Tag> : <Tag>无</Tag>),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
    { title: '排序', dataIndex: 'sort_order', width: 80 },
  ];

  return (
    <Card
      title="音色管理"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchProfiles}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>新增音色</Button>
        </Space>
      }
    >
      <Table rowKey="id" columns={columns} dataSource={profiles} loading={loading} />

      <Modal
        title="新增音色"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ provider: 'tts', voice_key: 'af_heart', is_active: true, sort_order: 0 }}
          onFinish={handleSubmit}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="例如：小月老师" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="provider" label="类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'tts', label: '普通 TTS 音色' },
                { value: 'openvoice', label: 'OpenVoice 克隆音色' },
              ]}
            />
          </Form.Item>
          <Form.Item name="voice_key" label="TTS voice 参数">
            <Input placeholder="af_heart" />
          </Form.Item>
          <Form.Item
            name="file"
            label="参考音频"
            valuePropName="fileList"
            getValueFromEvent={normalizeUpload}
          >
            <Upload beforeUpload={() => false} maxCount={1} accept=".wav,.mp3,.m4a,.webm,audio/*">
              <Button icon={<UploadOutlined />}>选择音频</Button>
            </Upload>
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
