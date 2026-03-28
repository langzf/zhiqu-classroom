import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Button, Space, Select, message, Popconfirm } from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  listConversations,
  createConversation,
  deleteConversation,
  type Conversation,
} from '@/api/tutor';

const SCENE_MAP: Record<string, { label: string; color: string }> = {
  qa: { label: '知识问答', color: 'blue' },
  explain: { label: '概念讲解', color: 'green' },
  exercise: { label: '练习辅导', color: 'orange' },
  general: { label: '自由对话', color: 'default' },
};

export default function ConversationList() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sceneFilter, setSceneFilter] = useState<string | undefined>();

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listConversations({
        scene: sceneFilter,
        page,
        page_size: pageSize,
      });
      setConversations(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [sceneFilter, page, pageSize]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleCreate = async () => {
    try {
      const conv = await createConversation({
        scene: 'general',
        title: `新对话 ${new Date().toLocaleString('zh-CN')}`,
      });
      message.success('创建成功');
      navigate(`/tutor/${conv.id}`);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '创建失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteConversation(id);
      message.success('删除成功');
      fetchConversations();
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const columns: ColumnsType<Conversation> = [
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (val: string, record: Conversation) => (
        <Button type="link" onClick={() => navigate(`/tutor/${record.id}`)}>
          {val || '(无标题)'}
        </Button>
      ),
    },
    {
      title: '场景',
      dataIndex: 'scene',
      width: 120,
      render: (val: string) => {
        const info = SCENE_MAP[val];
        return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>{val}</Tag>;
      },
    },
    {
      title: '消息数',
      dataIndex: 'message_count',
      width: 90,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      render: (val: boolean) => (
        <Tag color={val ? 'green' : 'default'}>{val ? '进行中' : '已结束'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (val: string) => (val ? new Date(val).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '最后更新',
      dataIndex: 'updated_at',
      width: 180,
      render: (val: string) => (val ? new Date(val).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作',
      width: 160,
      render: (_: unknown, record: Conversation) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<MessageOutlined />}
            onClick={() => navigate(`/tutor/${record.id}`)}
          >
            对话
          </Button>
          <Popconfirm
            title="确认删除该对话？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="AI 导师对话"
      extra={
        <Space>
          <Select
            placeholder="筛选场景"
            allowClear
            style={{ width: 140 }}
            value={sceneFilter}
            onChange={(val) => {
              setSceneFilter(val);
              setPage(1);
            }}
            options={Object.entries(SCENE_MAP).map(([k, v]) => ({
              label: v.label,
              value: k,
            }))}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchConversations}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建对话
          </Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        columns={columns}
        dataSource={conversations}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
      />
    </Card>
  );
}
