import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Space, Typography, Tag, Upload, Modal, Form, Input, Select, message } from 'antd';
import { PlusOutlined, UploadOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listTextbooks, createTextbook, uploadTextbook, triggerParse } from '@/api/content';
import type { Textbook } from '@zhiqu/shared';
import { SUBJECT_LABELS, PARSE_STATUS_LABELS } from '@zhiqu/shared';
import type { Subject, ParseStatus } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';

const { Title } = Typography;

const parseStatusColor: Record<string, string> = {
  pending: 'default',
  parsing: 'processing',
  completed: 'success',
  failed: 'error',
};

export default function TextbookList() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTextbooks({ page, page_size: 10 });
      setTextbooks(data.items);
      setTotal(data.total);
    } catch {
      message.error('加载教材列表失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (values: { title: string; subject: string; grade_range?: string }) => {
    try {
      await createTextbook({ title: values.title, subject: values.subject, grade: values.grade_range || '' });
      message.success('创建成功');
      setCreateOpen(false);
      form.resetFields();
      fetchData();
    } catch {
      message.error('创建失败');
    }
  };

  const handleUpload = async (values: { title: string; subject: string; file: { file: File } }) => {
    try {
      const file = (values.file as unknown as { file: File }).file;
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', values.title);
      formData.append('subject', values.subject);
      await uploadTextbook(formData);
      message.success('上传成功');
      setUploadOpen(false);
      form.resetFields();
      fetchData();
    } catch {
      message.error('上传失败');
    }
  };

  const handleParse = async (id: string) => {
    try {
      await triggerParse(id);
      message.success('解析任务已提交');
      fetchData();
    } catch {
      message.error('触发解析失败');
    }
  };

  const columns: ColumnsType<Textbook> = [
    { title: '教材名称', dataIndex: 'title', key: 'title' },
    {
      title: '科目',
      dataIndex: 'subject',
      key: 'subject',
      render: (v: Subject) => SUBJECT_LABELS[v] || v,
    },
    { title: '年级范围', dataIndex: 'grade_range', key: 'grade_range' },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'parse_status',
      render: (v: ParseStatus) => (
        <Tag color={parseStatusColor[v]}>{PARSE_STATUS_LABELS[v] || v}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => formatDate(v),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Textbook) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/textbooks/${record.id}`)}>
            详情
          </Button>
          {record.parse_status === 'pending' && (
            <Button type="link" onClick={() => handleParse(record.id)}>
              解析
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const subjectOptions = Object.entries(SUBJECT_LABELS).map(([k, v]) => ({
    value: k,
    label: v,
  }));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>教材管理</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>上传教材</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新建教材
          </Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={textbooks}
        columns={columns}
        pagination={{
          current: page,
          pageSize: 10,
          total,
          onChange: setPage,
        }}
      />

      {/* Create Modal */}
      <Modal
        title="新建教材"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="title" label="教材名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="subject" label="科目" rules={[{ required: true }]}>
            <Select options={subjectOptions} />
          </Form.Item>
          <Form.Item name="grade_range" label="年级范围">
            <Input placeholder="如：初一~初三" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>创建</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Upload Modal */}
      <Modal
        title="上传教材"
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={null}
      >
        <Form layout="vertical" onFinish={handleUpload}>
          <Form.Item name="title" label="教材名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="subject" label="科目" rules={[{ required: true }]}>
            <Select options={subjectOptions} />
          </Form.Item>
          <Form.Item name="file" label="文件" rules={[{ required: true }]}>
            <Upload beforeUpload={() => false} maxCount={1} accept=".pdf,.docx,.doc">
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>上传</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
