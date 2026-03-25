# AI Tutor API — AI 辅导

> 数据模型：[ai-tutor.md](../../data-model/ai-tutor.md) | 服务端口：`:8004`
> 服务前缀：`/api/v1`

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [conversations.md](./conversations.md) | 对话管理（创建/列表/详情/删除） |
| [messages.md](./messages.md) | 消息交互（同步回复/SSE 流式/请求提示/追问解释） |
| [feedback.md](./feedback.md) | 对话反馈 |
| [stats.md](./stats.md) | 辅导统计 & 知识薄弱点分析 |
| [internal.md](./internal.md) | 服务间接口（Internal） |
| [ai-behavior.md](./ai-behavior.md) | AI 行为规范（提示词/上下文管理/安全） |

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 | 详情 |
|------|------|------|------|------|
| POST | `/conversations` | 👤 student | 创建对话 | [→](./conversations.md#11-创建对话) |
| GET | `/conversations` | 👤 student | 我的对话列表 | [→](./conversations.md#12-对话列表) |
| GET | `/conversations/:id` | 👤 student | 对话详情 | [→](./conversations.md#13-对话详情) |
| DELETE | `/conversations/:id` | 👤 student | 删除对话 | [→](./conversations.md#14-删除对话) |
| POST | `/conversations/:id/messages` | 👤 student | 发送消息（同步） | [→](./messages.md#21-发送消息同步) |
| POST | `/conversations/:id/messages` | 👤 student | 发送消息（SSE 流式） | [→](./messages.md#22-发送消息sse-流式) |
| POST | `/conversations/:id/hint` | 👤 student | 请求提示 | [→](./messages.md#23-请求提示) |
| GET | `/conversations/:id/messages/:msgId/explain` | 👤 student | 追问解释 | [→](./messages.md#24-追问解释) |
| POST | `/conversations/:id/feedback` | 👤 student | 对话反馈 | [→](./feedback.md) |
| GET | `/tutor/stats` | 👤 student | 我的辅导统计 | [→](./stats.md#41-我的辅导统计) |
| GET | `/tutor/stats/overview` | 🛡️ teacher/admin | 辅导使用概览 | [→](./stats.md#42-辅导使用概览) |
| GET | `/tutor/knowledge-gaps` | 👤 student | 知识薄弱点分析 | [→](./stats.md#43-知识薄弱点分析) |

---

## 通用说明

### 认证

所有接口需携带 JWT Token：

```
Authorization: Bearer <access_token>
```

### 响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... },
  "request_id": "req-uuid"
}
```

### 错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| 50001 | 400 | 对话不存在或已删除 |
| 50002 | 400 | 消息为空或超过长度限制 |
| 50003 | 429 | 对话频率限制（每分钟最多 10 条） |
| 50004 | 400 | 对话关联的知识点无效 |
| 50005 | 500 | LLM 服务暂时不可用 |
| 50006 | 400 | 对话上下文超过窗口限制 |
| 50007 | 400 | 不支持的消息类型 |
| 50008 | 429 | 每日对话数量已达上限 |
| 50009 | 400 | 反馈已提交，不可重复 |

### 枚举定义

**context_type — 对话场景**

| 值 | 说明 |
|----|------|
| `knowledge_point` | 针对特定知识点的辅导 |
| `task` | 在做任务时遇到问题 |
| `free` | 自由提问 |

**rating — 反馈评级**

| 值 | 说明 |
|----|------|
| `helpful` | 有帮助 |
| `not_helpful` | 没帮助 |
| `confusing` | 表述混乱 |
| `incorrect` | 内容有误 |

**content_type — 消息内容类型**

| 值 | 说明 |
|----|------|
| `text` | 纯文本（默认） |
| `image` | 图片（OCR → 文本后处理） |
