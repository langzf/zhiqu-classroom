import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Descriptions, Button, Spin, Tree, Typography, Tag, Card, Space, Empty, Collapse, message } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
import { getTextbook, getChapters, listKnowledgePoints, triggerParse } from '@/api/content';
import type { Textbook, Chapter, KnowledgePoint } from '@zhiqu/shared';
import { SUBJECT_LABELS, PARSE_STATUS_LABELS, formatDate } from '@zhiqu/shared';
import type { Subject, ParseStatus } from '@zhiqu/shared';
import type { DataNode } from 'antd/es/tree';

const { Text } = Typography;

const parseStatusColor: Record<string, string> = {
  pending: 'default',
  parsing: 'processing',
  completed: 'success',
  failed: 'error',
};

function chaptersToTree(chapters: Chapter[]): DataNode[] {
  const map = new Map<string, DataNode & { children: DataNode[] }>();
  const roots: DataNode[] = [];

  for (const ch of chapters) {
    map.set(ch.id, { key: ch.id, title: ch.title, children: [] });
  }
  for (const ch of chapters) {
    const node = map.get(ch.id)!;
    if (ch.parent_id && map.has(ch.parent_id)) {
      map.get(ch.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

export default function TextbookDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [textbook, setTextbook] = useState<Textbook | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
  const [knowledgePoints, setKnowledgePoints] = useState<KnowledgePoint[]>([]);
  const [kpLoading, setKpLoading] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [tb, chs] = await Promise.all([getTextbook(id), getChapters(id)]);
      setTextbook(tb);
      setChapters(chs);
    } catch {
      message.error('加载教材详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleSelectChapter = async (chapterId: string) => {
    setSelectedChapter(chapterId);
    setKpLoading(true);
    try {
      const res = await listKnowledgePoints({ chapter_id: chapterId, page: 1, page_size: 200 });
      setKnowledgePoints(res.items);
    } catch {
      message.error('加载知识点失败');
    } finally {
      setKpLoading(false);
    }
  };

  const handleParse = async () => {
    if (!id) return;
    try {
      await triggerParse(id);
      message.success('解析任务已提交');
      fetchDetail();
    } catch {
      message.error('触发解析失败');
    }
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!textbook) return <Empty description="教材不存在" />;

  const treeData = chaptersToTree(chapters);
  const selectedChapterObj = chapters.find((c) => c.id === selectedChapter);

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/textbooks')}>
          返回
        </Button>
        <Button icon={<ReloadOutlined />} onClick={fetchDetail}>刷新</Button>
        {textbook.parse_status === 'pending' && (
          <Button type="primary" onClick={handleParse}>触发解析</Button>
        )}
      </Space>

      <Descriptions title={textbook.title} bordered column={2}>
        <Descriptions.Item label="科目">
          {SUBJECT_LABELS[textbook.subject as Subject] || textbook.subject}
        </Descriptions.Item>
        <Descriptions.Item label="年级范围">{textbook.grade_range || '-'}</Descriptions.Item>
        <Descriptions.Item label="解析状态">
          <Tag color={parseStatusColor[textbook.parse_status]}>
            {PARSE_STATUS_LABELS[textbook.parse_status as ParseStatus] || textbook.parse_status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatDate(textbook.created_at)}</Descriptions.Item>
      </Descriptions>

      <div style={{ display: 'flex', gap: 24, marginTop: 24 }}>
        {/* Chapter Tree */}
        <Card title="章节目录" style={{ width: 300, flexShrink: 0 }}>
          {treeData.length > 0 ? (
            <Tree
              treeData={treeData}
              defaultExpandAll
              onSelect={(keys) => {
                if (keys.length > 0) handleSelectChapter(keys[0] as string);
              }}
              selectedKeys={selectedChapter ? [selectedChapter] : []}
            />
          ) : (
            <Empty description="暂无章节" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        {/* Knowledge Points */}
        <Card
          title={selectedChapterObj ? `${selectedChapterObj.title} - 知识点` : '知识点'}
          style={{ flex: 1 }}
        >
          {kpLoading ? (
            <Spin />
          ) : knowledgePoints.length > 0 ? (
            <Collapse
              items={knowledgePoints.map((kp) => ({
                key: kp.id,
                label: (
                  <Space>
                    <Text strong>{kp.title}</Text>
                    <Tag color="blue">难度 {kp.difficulty}</Tag>
                    {kp.bloom_level && <Tag color="orange">{kp.bloom_level}</Tag>}
                  </Space>
                ),
                children: (
                  <div>
                    <Text>{kp.description || '暂无描述'}</Text>
                    {kp.tags && Object.keys(kp.tags).length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        {Object.entries(kp.tags).map(([k, v]) => (
                          <Tag key={k}>{`${k}: ${v}`}</Tag>
                        ))}
                      </div>
                    )}
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty
              description={selectedChapter ? '该章节暂无知识点' : '请选择章节查看知识点'}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Card>
      </div>
    </div>
  );
}
