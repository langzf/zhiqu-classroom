# Task: Content Engine - File Upload & Parse Pipeline (P0)

## Project
- Root: `C:\Users\18513\.openclaw\workspace\zhiqu-classroom`
- Python venv: `.venv\Scripts\python.exe`
- Services dir: `services/`
- Config: `services/.env` and `services/config.py`

## Context
This is a FastAPI monolith for an AI education app (zhiqu-classroom).
The content_engine module has CRUD skeleton code but is missing the core upload→parse→extract pipeline.

## Infrastructure (all running in Docker)
- PostgreSQL 16 + pgvector on localhost:5432, db=zhiqu, user=postgres, pw=postgres
- Redis 7 on localhost:6379
- MinIO on localhost:9000, user=minioadmin, pw=minioadmin, bucket=zhiqu
- FastAPI runs on port 8001 (8000 occupied)

## What Exists
- `services/content_engine/models.py` - ORM models: Textbook, Chapter, KnowledgePoint, KpEmbedding, GeneratedResource, PromptTemplate
- `services/content_engine/router.py` - Routes with create_textbook (JSON body only), list/get textbooks, trigger_parse (stub), knowledge_points CRUD, vector_search
- `services/content_engine/service.py` - ContentService class with CRUD methods. `trigger_parse` only flips status to "parsing", no actual parsing. `vector_search` does real pgvector query.
- `services/content_engine/schemas.py` - Pydantic schemas
- `services/shared/llm_client.py` - LLMClient wrapper around openai AsyncOpenAI SDK, initialized in main.py lifespan as `app.state.llm_client`
- `services/config.py` - Settings with minio_endpoint, minio_access_key, minio_secret_key, minio_bucket, llm_base_url, llm_model, llm_api_key
- `services/main.py` - FastAPI app with lifespan that inits Redis, LLM client, registers routers. MinIO is NOT initialized here yet.

## What to Implement (in order)

### Step 1: MinIO Client Initialization
- Create `services/shared/minio_client.py`:
  - Sync MinIO client using `minio` package (it's sync, that's fine for MVP)
  - `init_minio(settings) -> Minio`: creates client, ensures bucket exists
  - Store on `app.state.minio_client` in lifespan
- Update `services/main.py` lifespan to call `init_minio` and store result

### Step 2: File Upload Endpoint
- Add `POST /api/v1/content/textbooks/upload` to router
- Accept `UploadFile` (PDF or DOCX only, max 50MB)
- Also accept form fields: `title`, `subject`, `grade_range`
- Upload file to MinIO under path `textbooks/{uuid7}/{filename}`
- Create Textbook record with `parse_status="pending"`, `source_file_url=minio_path`
- Return textbook info

### Step 3: Document Parser
- Create `services/content_engine/parser.py`:
  - `parse_pdf(file_bytes) -> ParseResult` using PyMuPDF (fitz)
  - `parse_docx(file_bytes) -> ParseResult` using python-docx
  - `ParseResult` = dataclass with `full_text: str`, `chapters: list[ChapterInfo]`
  - `ChapterInfo` = dataclass with `title: str`, `level: int`, `content: str`, `children: list[ChapterInfo]`
  - For PDF: extract text page by page, detect headings by font size heuristics
  - For DOCX: use heading styles (Heading 1-4) to build chapter tree
  - Keep it simple for MVP - basic extraction is fine

### Step 4: Sync Parse Pipeline
- Update `trigger_parse` in service.py:
  - Download file from MinIO
  - Detect file type (pdf/docx) from extension
  - Call parser to get ParseResult
  - Save chapters to DB (recursive, with parent_id and sort_order)
  - Update textbook parse_status to "parsed" on success, "failed" on error
  - Store full_text in textbook.metadata JSONB for later use
- Update the router's trigger_parse endpoint to call the real implementation
- Make it synchronous for MVP (no background worker)

### Step 5: Knowledge Point Extraction via LLM
- Add method `extract_knowledge_points(textbook_id)` to ContentService:
  - Load all chapters for the textbook
  - For each chapter with content, call LLM to extract knowledge points
  - Prompt: "Extract knowledge points from this chapter text. Return JSON array with: name, description, difficulty (1-5), bloom_level, tags"
  - Save extracted KPs to knowledge_points table linked to chapter_id
  - Use `app.state.llm_client` (LLMClient from shared/llm_client.py)
  - If no LLM API key configured, log warning and skip (don't crash)
- Add endpoint `POST /api/v1/content/textbooks/{id}/extract-kp` to trigger extraction

### Step 6: Missing Service Method
- Add `get_generated_resource(db, resource_id)` to ContentService - the router calls it but it doesn't exist in service.py. Simple get-by-id with NotFoundError.

## Technical Constraints
- Use existing patterns: structlog for logging, shared.exceptions for errors, shared.schemas for response wrapping
- All DB operations use async SQLAlchemy (AsyncSession)
- MinIO client is sync (that's the library's nature), wrap in run_in_executor if needed for async endpoints
- UUID v7 for all new record IDs (use `uuid6.uuid7()`)
- Keep consistent with existing code style
- Don't modify models.py unless absolutely necessary (tables already created)
- Textbook.parse_status values: "pending" → "parsing" → "parsed" / "failed"

## Testing After Implementation
Run the server and test:
```bash
cd services
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Test upload with curl:
```bash
curl -X POST http://localhost:8001/api/v1/content/textbooks/upload -F "file=@test.pdf" -F "title=测试教材" -F "subject=math" -F "grade_range=七年级"
```

## Installed Packages (confirmed)
minio, pymupdf (fitz), python-docx, openai, pdfplumber - all installed in .venv
