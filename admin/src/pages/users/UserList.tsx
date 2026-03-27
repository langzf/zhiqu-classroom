import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Typography, Tag, message, Input, Space, Select,
} from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listUsers } from '@/api/user';
import type { User } from '@zhiqu/shared';
import { ROLE_LABELS } from '@zhiqu/shared';
import { formatDate } from '@zhiqu/shared';

const { Title } = Typography;

const roleColors: Record<string, string> = {
  student: 'blue',
  guardian: 'green',
  admin: 'red',
};

export default function UserList() {
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listUsers({
        page,
        page_size: 20,
        search: search || undefined,
        role: roleFilter,
      });
      // Handle both paginated and array responses
      if (Array.isArray(data)) {
        setUsers(data);
        setTotal(data.length);
      } else {
        setUsers(data.items || []);
        setTotal(data.total || 0);
      }
    } catch {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns: ColumnsType<User> = [
    {
      title: '昵称',
      dataIndex: 'nickname',
      key: 'nickname',
      width: 150,
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      key: 'phone',
      width: 140,
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (v: string) => (
        <Tag color={roleColors[v] || 'default'}>
          {ROLE_LABELS[v] || v}
        </Tag>
      ),
    },
    {
      title: '注册时间',
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
      render: (v: string) => v ? formatDate(v) : '-',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>用户管理</Title>
        <Space>
          <Input
            placeholder="搜索昵称/手机号"
            prefix={<SearchOutlined />}
            value={search}
            onChange={e => setSearch(e.target.value)}
            onPressEnter={() => { setPage(1); fetchData(); }}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            allowClear
            placeholder="角色"
            style={{ width: 120 }}
            value={roleFilter}
            onChange={v => { setRoleFilter(v); setPage(1); }}
            options={Object.entries(ROLE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={users}
        columns={columns}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 位用户`,
        }}
      />
    </div>
  );
}
