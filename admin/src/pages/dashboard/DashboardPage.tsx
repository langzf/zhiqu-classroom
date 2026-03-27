import { Typography, Card, Row, Col, Statistic } from 'antd';
import { BookOutlined, FileTextOutlined, ExperimentOutlined, UserOutlined } from '@ant-design/icons';

const { Title } = Typography;

export default function DashboardPage() {
  return (
    <div>
      <Title level={4}>仪表盘</Title>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="教材总数" value={0} prefix={<BookOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="知识点" value={0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="练习题" value={0} prefix={<ExperimentOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="用户数" value={0} prefix={<UserOutlined />} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
