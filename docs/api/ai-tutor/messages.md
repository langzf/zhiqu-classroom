# 2. 消息交互

> 父文档：[README.md](./README.md)

---

## 2.1 发送消息（同步）

```
POST /api/v1/conversations/:id/messages
```

发送学生消息并获取 AI 回复。同步模式下等待 AI 完整回复后返回。

**Request Body**

```json
{
  "content": "那负数加负数呢？比如 -3 + (-5) 怎么算？",
  "content_type": "text"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | ✅ | 消息内容，最长 2000 字 |
| content_type | string | | `text`（默认）/ `image`（图片 OCR → 文本） |
| image_url | string | 条件 | `content_type=image` 时必填，图片 URL |
| metadata | object | | 客户端附加信息（如题目截图区域坐标） |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_message": {
      "id": "msg-uuid-3",
      "role": "user",
      "content": "那负数加负数呢？比如 -3 + (-5) 怎么算？",
      "created_at": "2026-03-25T19:02:00+08:00"
    },
    "assistant_message": {
      "id": "msg-uuid-4",
      "role": "assistant",
      "content": "很好的追问！负数加负数的规则是：\n\n**同号相加，取相同的符号，绝对值相加。**\n\n所以 -3 + (-5) = -(3+5) = -8\n\n你可以这样理解...",
      "content_type": "text",
      "thinking_steps": [
        "学生在追问负数加法的具体情况",
        "需要给出同号相加的法则",
        "用具体例子演示",
        "引导性结尾，保持苏格拉底式教学"
      ],
      "knowledge_refs": [
        { "id": "kp-uuid-1", "name": "有理数的加法" }
      ],
      "token_usage": { "prompt": 580, "completion": 240 },
      "created_at": "2026-03-25T19:02:03+08:00"
    }
  }
}
```

---

## 2.2 发送消息（SSE 流式）

```
POST /api/v1/conversations/:id/messages
```

通过 `Accept: text/event-stream` 请求流式响应。适用于前端逐字显示 AI 回复。

**Request Headers**

```
Content-Type: application/json
Accept: text/event-stream
```

**Request Body** — 同 2.1 同步接口。

**SSE 事件流**

```
event: message_created
data: {"user_message_id": "msg-uuid-3", "assistant_message_id": "msg-uuid-4"}

event: delta
data: {"content": "很好的"}

event: delta
data: {"content": "追问！"}

event: delta
data: {"content": "负数加负数的规则是：\n\n"}

event: thinking
data: {"step": "学生在追问负数加法的具体情况"}

event: thinking
data: {"step": "需要给出同号相加的法则"}

event: delta
data: {"content": "**同号相加，取相同的符号，绝对值相加。**"}

...

event: done
data: {"message_id": "msg-uuid-4", "token_usage": {"prompt": 580, "completion": 240}, "knowledge_refs": [{"id": "kp-uuid-1", "name": "有理数的加法"}]}
```

**SSE 事件类型**

| 事件 | 说明 |
|------|------|
| `message_created` | 消息对创建，返回两条消息的 ID |
| `delta` | AI 回复的增量文本片段 |
| `thinking` | AI 的思考步骤（可选，前端可折叠展示） |
| `done` | 回复完成，附带 token 用量和知识点引用 |
| `error` | 出错，附带错误码和描述 |

**错误事件示例**

```
event: error
data: {"code": 50005, "message": "LLM 服务暂时不可用，请稍后重试"}
```

---

## 2.3 请求提示

```
POST /api/v1/conversations/:id/hint
```

学生遇到困难时请求提示，AI 给出引导性提示但**不直接给出答案**。采用苏格拉底式教学法。

**Request Body**

```json
{
  "context": "我在做这道题但不知道怎么开始：计算 -7 + 3 + (-2) + 8",
  "hint_level": 1
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| context | string | ✅ | 当前困惑的描述或题目 |
| hint_level | int | | 提示级别 1-3，默认 1（越高越直接） |

> **提示级别：**
> - **Level 1**：方向性提示（"你可以想想正数和负数分别是多少"）
> - **Level 2**：方法提示（"先把正数加在一起，再把负数加在一起"）
> - **Level 3**：步骤提示（"正数：3+8=11，负数：-7+(-2)=-9，然后..."）

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "hint_message": {
      "id": "msg-uuid-5",
      "role": "assistant",
      "content": "💡 这道题有多个数相加，你可以试试把它们分成两组——正数一组、负数一组，分别算完再合并。你觉得哪些是正数，哪些是负数呢？",
      "hint_level": 1,
      "created_at": "2026-03-25T19:05:00+08:00"
    }
  }
}
```

---

## 2.4 追问解释

```
GET /api/v1/conversations/:id/messages/:msgId/explain
```

对 AI 某条回复中的某个概念请求更详细的解释。

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| term | string | 要解释的概念/术语（如 "绝对值"） |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "explanation": {
      "id": "msg-uuid-6",
      "role": "assistant",
      "content": "**绝对值**就是一个数到 0 的距离，不管方向，所以永远是非负数。\n\n比如：\n- |5| = 5（正数的绝对值是它本身）\n- |-5| = 5（负数的绝对值去掉负号）\n- |0| = 0\n\n你可以想象数轴上，绝对值就是一个点离原点有多远。",
      "term": "绝对值",
      "knowledge_refs": [
        { "id": "kp-uuid-2", "name": "绝对值" }
      ],
      "created_at": "2026-03-25T19:06:00+08:00"
    }
  }
}
```
