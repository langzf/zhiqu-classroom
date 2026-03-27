import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Space, Typography, Tag, message, Modal } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listConversations, createConversation, archiveConversation } from '@/api/tutor';
import type { Conversation } from '@zhiqu/shared';
import { SUBJECT_LABELS } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';
import type { Subject } from '@zhiqu/shared';

const { Title } = Typography;

const statusColor: Record<string, string> = {
  active: 'green',
  archived: 'default',
};
const statusLabel: Record<string, string> = {
  active: '进行中',
  archived: '已归档',
};

export default function ConversationList() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listConversations({ limit: 50 });
      setConversations(data);
    } catch {
      message.error('加载会话列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async () => {
    try {
      const conv = await createConversation({ title: '新对话' });
      message.success('创建成功');
      navigate(`/tutor/${conv.id}`);
    } catch {
      message.error('创建失败');
    }
  };

  const handleArchive = (id: string) => {
    Modal.confirm({
      title: '确认归档',
      content: '归档后该会话将不可继续对话，确认归档吗？',
      onOk: async () => {
        try {
          await archiveConversation(id);
          message.success('已归档');
          fetchData();
        } catch {
          message.error('归档失败');
        }
      },
    });
  };

  const columns: ColumnsType<Conversation> = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '科目',
      dataIndex: 'subject',
      key: 'subject',
      width: 100,
      render: (v: Subject | null) => v ? (SUBJECT_LABELS[v] || v) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => <Tag color={statusColor[v]}>{statusLabel[v] || v}</Tag>,
    },
    {
      title: '消息数',
      dataIndex: 'message_count',
      key: 'message_count',
      width: 80,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string) => formatDate(v),
    },
    {
      title: '最后活跃',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      render: (v: string) => formatDate(v),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: Conversation) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/tutor/${record.id}`)}>
            {record.status === 'active' ? '对话' : '查看'}
          </Button>
          {record.status === 'active' && (
            <Button type="link" danger onClick={() => handleArchive(record.id)}>
              归档
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>AI 辅导对话</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建对话
          </Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={conversations}
        columns={columns}
        pagination={{ pageSize: 20 }}
      />
    </div>
  );
}
