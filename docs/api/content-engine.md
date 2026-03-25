# Content Engine API — 教材与知识点

> 父文档：[README.md](./README.md) | 数据模型：[data-model.md](../data-model.md) course schema  
> 服务前缀：`/api/v1`

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | `/textbooks` | 🛡️ admin | 创建教材 |
| GET | `/textbooks` | 👤 all | 教材列表 |
| GET | `/textbooks/:id` | 👤 all | 教材详情 |
| PATCH | `/textbooks/:id` | 🛡️ admin | 更新教材 |
| DELETE | `/textbooks/:id` | 🛡️ admin | 删除教材（软删除） |
| POST | `/textbooks/:id/parse` | 🛡️ admin | 触发 AI 解析教材 |
| GET | `/textbooks/:id/parse-status` | 🛡️ admin | 查询解析进度 |
| GET | `/textbooks/:id/chapters` | 👤 all | 教材章节树 |
| POST | `/textbooks/:id/chapters` | 🛡️ admin | 手动添加章节 |
| PATCH | `/chapters/:id` | 🛡️ admin | 更新章节 |
| DELETE | `/chapters/:id` | 🛡️ admin | 删除章节 |
| GET | `/chapters/:id/knowledge-points` | 👤 all | 章节下知识点 |
| POST | `/chapters/:id/knowledge-points` | 🛡️ admin | 添加知识点 |
| PATCH | `/knowledge-points/:id` | 🛡️ admin | 更新知识点 |
| DELETE | `/knowledge-points/:id` | 🛡️ admin | 删除知识点 |
| POST | `/knowledge-points/batch` | 🛡️ admin | 批量导入知识点 |

---

## 1. 教材管理

### 1.1 创建教材

```
POST /api/v1/textbooks
```

**Request Body**

```json
{
  "title": "人教版数学七年级上册",
  "subject": "math",
  "grade": "grade_7",
  "publisher": "人民教育出版社",
  "edition": "2024版",
  "cover_url": "https://oss.example.com/covers/math-7-up.jpg",
  "description": "人教版初中数学七年级上册教材"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 教材名称 |
| subject | string | ✅ | 学科枚举（见下方） |
| grade | string | ✅ | 年级：`grade_1` ~ `grade_12` |
| publisher | string | ✅ | 出版社 |
| edition | string | | 版次 |
| cover_url | string | | 封面图 URL |
| description | string | | 描述 |

> **学科枚举**：`math` / `chinese` / `english` / `physics` / `chemistry` / `biology` / `history` / `geography` / `politics`

**Response** `201`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "title": "人教版数学七年级上册",
    "subject": "math",
    "grade": "grade_7",
    "publisher": "人民教育出版社",
    "edition": "2024版",
    "cover_url": "...",
    "status": "draft",
    "created_at": "2026-03-25T15:00:00+08:00"
  }
}
```

### 1.2 教材列表

```
GET /api/v1/textbooks
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| subject | string | 按学科筛选 |
| grade | string | 按年级筛选 |
| publisher | string | 按出版社筛选 |
| status | string | `draft` / `published` / `archived` |
| keyword | string | 模糊搜索标题 |
| page | int | 页码，默认 1 |
| page_size | int | 每页条数，默认 20 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "人教版数学七年级上册",
        "subject": "math",
        "grade": "grade_7",
        "publisher": "人民教育出版社",
        "status": "published",
        "chapter_count": 8,
        "knowledge_point_count": 42,
        "created_at": "..."
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

### 1.3 教材详情

```
GET /api/v1/textbooks/:id
```

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "title": "人教版数学七年级上册",
    "subject": "math",
    "grade": "grade_7",
    "publisher": "人民教育出版社",
    "edition": "2024版",
    "cover_url": "...",
    "description": "...",
    "status": "published",
    "source_file_url": "https://oss.example.com/textbooks/math-7-up.pdf",
    "chapter_count": 8,
    "knowledge_point_count": 42,
    "parse_status": "completed",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### 1.4 更新教材

```
PATCH /api/v1/textbooks/:id
```

**Request Body** — 仅传需要更新的字段。

```json
{
  "title": "人教版数学七年级上册（修订）",
  "status": "published"
}
```

**Response** `200` — 返回更新后的完整教材对象。

### 1.5 删除教材

```
DELETE /api/v1/textbooks/:id
```

软删除（设置 `deleted_at`）。已发布且有关联学习记录的教材不可删除，返回 `41002`。

**Response** `200`

```json
{ "code": 0, "message": "ok", "data": null }
```

---

## 2. AI 解析教材

### 2.1 触发解析

```
POST /api/v1/textbooks/:id/parse
```

上传教材文件 → 异步 AI 解析（提取章节结构 + 知识点）。

**Request Body**

```json
{
  "file_url": "https://oss.example.com/uploads/math-7-up.pdf",
  "file_type": "pdf",
  "options": {
    "extract_chapters": true,
    "extract_knowledge_points": true,
    "ocr_enabled": false
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_url | string | ✅ | 已上传到 OSS 的文件地址 |
| file_type | string | ✅ | `pdf` / `docx` / `pptx` |
| options.extract_chapters | bool | | 默认 true |
| options.extract_knowledge_points | bool | | 默认 true |
| options.ocr_enabled | bool | | 扫描件 OCR，默认 false |

**Response** `202 Accepted`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task-uuid",
    "status": "pending",
    "estimated_duration_s": 120
  }
}
```

### 2.2 查询解析进度

```
GET /api/v1/textbooks/:id/parse-status
```

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task-uuid",
    "status": "processing",
    "progress_pct": 65,
    "current_step": "提取第5章知识点",
    "steps": [
      { "name": "文档解析", "status": "completed" },
      { "name": "章节提取", "status": "completed" },
      { "name": "知识点提取", "status": "processing" },
      { "name": "质量校验", "status": "pending" }
    ],
    "started_at": "2026-03-25T15:01:00+08:00",
    "estimated_completion_at": "2026-03-25T15:03:00+08:00"
  }
}
```

解析完成后章节和知识点自动写入对应表，教材 `parse_status` → `completed`。

---

## 3. 章节管理

### 3.1 章节树

```
GET /api/v1/textbooks/:id/chapters
```

返回树形结构（支持多级嵌套：单元 → 课 → 节，最多 3 级）。

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": "chapter-uuid-1",
      "title": "第一章 有理数",
      "sort_order": 1,
      "level": 1,
      "knowledge_point_count": 8,
      "children": [
        {
          "id": "chapter-uuid-1-1",
          "title": "1.1 正数和负数",
          "sort_order": 1,
          "level": 2,
          "knowledge_point_count": 3,
          "children": []
        }
      ]
    }
  ]
}
```

### 3.2 添加章节

```
POST /api/v1/textbooks/:id/chapters
```

**Request Body**

```json
{
  "title": "第一章 有理数",
  "parent_id": null,
  "sort_order": 1,
  "description": "有理数的概念与运算"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 章节标题 |
| parent_id | uuid | | 父章节 ID，null 为顶级 |
| sort_order | int | | 排序序号，默认追加末尾 |
| description | string | | 章节描述 |

**Response** `201`

### 3.3 更新章节

```
PATCH /api/v1/chapters/:id
```

支持更新 `title`、`sort_order`、`description`、`parent_id`（移动章节）。

### 3.4 删除章节

```
DELETE /api/v1/chapters/:id
```

级联软删除子章节和关联知识点。有学习记录时拒绝删除（`41010`）。

---

## 4. 知识点管理

### 4.1 章节下知识点列表

```
GET /api/v1/chapters/:id/knowledge-points
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| difficulty | string | `basic` / `intermediate` / `advanced` |
| page | int | 页码 |
| page_size | int | 每页条数 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "kp-uuid-1",
        "chapter_id": "chapter-uuid",
        "name": "正数和负数的概念",
        "description": "正数：大于0的数；负数：小于0的数",
        "difficulty": "basic",
        "sort_order": 1,
        "prerequisites": [],
        "tags": ["概念", "有理数"],
        "created_at": "..."
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.2 添加知识点

```
POST /api/v1/chapters/:id/knowledge-points
```

**Request Body**

```json
{
  "name": "正数和负数的概念",
  "description": "正数：大于0的数；负数：小于0的数；0既不是正数也不是负数",
  "difficulty": "basic",
  "sort_order": 1,
  "prerequisites": ["kp-uuid-prev"],
  "tags": ["概念", "有理数"],
  "metadata": {
    "bloom_level": "remember",
    "estimated_minutes": 15
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 知识点名称 |
| description | string | | 详细描述 |
| difficulty | string | | `basic`（默认）/ `intermediate` / `advanced` |
| sort_order | int | | 排序 |
| prerequisites | uuid[] | | 前置知识点 ID |
| tags | string[] | | 标签 |
| metadata | object | | 扩展：布鲁姆层级、预估时长等 |

**Response** `201`

### 4.3 更新知识点

```
PATCH /api/v1/knowledge-points/:id
```

### 4.4 删除知识点

```
DELETE /api/v1/knowledge-points/:id
```

### 4.5 批量导入知识点

```
POST /api/v1/knowledge-points/batch
```

**Request Body**

```json
{
  "chapter_id": "chapter-uuid",
  "items": [
    { "name": "正数和负数的概念", "description": "...", "difficulty": "basic" },
    { "name": "有理数的分类", "description": "...", "difficulty": "basic" }
  ],
  "overwrite_existing": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| chapter_id | uuid | ✅ | 目标章节 |
| items | array | ✅ | 知识点列表，最多 100 条 |
| overwrite_existing | bool | | 同名覆盖，默认 false |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "created": 8, "updated": 2, "skipped": 1, "errors": [] }
}
```

---

## 5. 错误码

| 错误码 | 说明 |
|--------|------|
| 41001 | 教材不存在 |
| 41002 | 教材有关联数据，不可删除 |
| 41003 | 教材解析任务正在进行中 |
| 41004 | 不支持的文件类型 |
| 41010 | 章节不存在或有关联数据 |
| 41011 | 章节嵌套层级超限（最多 3 级） |
| 41020 | 知识点不存在 |
| 41021 | 批量导入数量超限（最多 100） |
| 41022 | 前置知识点不存在或循环依赖 |
