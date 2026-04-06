import { Tabs } from 'antd';
import { ApiOutlined, SettingOutlined, LinkOutlined } from '@ant-design/icons';
import ProviderList from './ProviderList';
import ModelConfigList from './ModelConfigList';
import SceneBindingList from './SceneBindingList';

const items = [
  {
    key: 'providers',
    label: (
      <span><ApiOutlined /> 供应商管理</span>
    ),
    children: <ProviderList />,
  },
  {
    key: 'configs',
    label: (
      <span><SettingOutlined /> 模型配置</span>
    ),
    children: <ModelConfigList />,
  },
  {
    key: 'scenes',
    label: (
      <span><LinkOutlined /> 场景绑定</span>
    ),
    children: <SceneBindingList />,
  },
];

export default function ModelConfigPage() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>模型配置管理</h2>
      <Tabs items={items} defaultActiveKey="providers" />
    </div>
  );
}
