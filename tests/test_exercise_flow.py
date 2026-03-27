"""
Step 5: 手动测试练习题生成完整流程
1. 签发测试 JWT
2. 创建教材
3. 直接在DB中创建章节和知识点（跳过解析，避免依赖文件上传）
4. 创建 prompt 模板
5. 生成练习题
6. 查询练习题
"""
import asyncio
import json
import sys
import os

# 让 import 能找到 services/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

import httpx

BASE = "http://localhost:8001"

# ── Step 1: 签发 admin token ──
from shared.security import JWTManager

jwt_mgr = JWTManager("dev-secret-change-in-production", "HS256")
ADMIN_TOKEN = jwt_mgr.create_access_token(
    user_id="test-admin-001",
    role="admin",
    expires_minutes=60,
)
HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def pp(label: str, r: httpx.Response):
    """Pretty-print response"""
    status = "OK" if r.status_code < 400 else "FAIL"
    print(f"\n{status} [{r.status_code}] {label}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
    except Exception:
        print(r.text[:500])


async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=60) as c:
        # ── Step 2: 创建教材 ──
        print("=" * 60)
        print("STEP 2: 创建教材")
        r = await c.post("/api/v1/content/textbooks", json={
            "title": "测试数学教材",
            "subject": "数学",
            "grade_range": "七年级上",
            "source_file_url": "http://minio:9000/zhiqu/test/placeholder.pdf"
        })
        pp("创建教材", r)
        if r.status_code >= 400:
            print("创建教材失败，退出")
            return
        textbook_id = r.json()["data"]["id"]
        print(f"  textbook_id = {textbook_id}")

        # ── Step 3: 直接在 DB 中创建章节和知识点 ──
        print("\n" + "=" * 60)
        print("STEP 3: 在 DB 中创建章节和知识点")
        
        # 使用 SQLAlchemy 直接操作数据库
        from database import engine as async_engine
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker as orm_sessionmaker
        from sqlalchemy import text
        from uuid6 import uuid7
        
        async_session = orm_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        
        chapter_id = str(uuid7())
        kp_id = str(uuid7())
        
        async with async_session() as session:
            # 创建章节
            await session.execute(text("""
                INSERT INTO content.chapters (id, textbook_id, title, sort_order, depth)
                VALUES (:id, :tid, :title, :ord, :lvl)
            """), {
                "id": chapter_id,
                "tid": textbook_id,
                "title": "第一章 有理数",
                "ord": 1,
                "lvl": 1,
            })
            
            # 创建知识点
            await session.execute(text("""
                INSERT INTO content.knowledge_points (id, chapter_id, title, description, difficulty)
                VALUES (:id, :cid, :title, :desc, :diff)
            """), {
                "id": kp_id,
                "cid": chapter_id,
                "title": "有理数的加法",
                "desc": "有理数加法运算法则：同号相加取相同符号，绝对值相加；异号相加取绝对值较大的符号，绝对值相减。",
                "diff": 3,
            })
            await session.commit()
        
        print(f"  ✅ chapter_id = {chapter_id}")
        print(f"  ✅ kp_id = {kp_id}")
        
        # 验证知识点可以查到
        r = await c.get(f"/api/v1/content/knowledge-points/{kp_id}")
        pp("查询知识点", r)

        # ── Step 4: 查看/创建 prompt 模板 ──
        print("\n" + "=" * 60)
        print("STEP 4: Prompt 模板")
        
        r = await c.get("/api/v1/content/prompts", params={"resource_type": "exercise_choice"})
        pp("查询已有 choice 模板", r)
        
        existing = r.json().get("data", [])
        if existing:
            print("  已有模板，跳过创建")
        else:
            r = await c.post("/api/v1/content/prompts", json={
                "resource_type": "exercise_choice",
                "name": "选择题默认模板",
                "template_text": """你是一位资深的{subject}教师。请根据以下知识点生成{count}道选择题。

知识点：{kp_name}
知识点描述：{kp_description}
难度等级：{difficulty}（1-5，5最难）

要求：
1. 每道题有4个选项（A/B/C/D）
2. 题目难度与指定等级匹配
3. 题干清晰，选项合理
4. 提供正确答案和详细解析

请以JSON格式输出：
{{"questions": [{{"id": 1, "stem": "题干", "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}}, "answer": "B", "explanation": "解析", "difficulty": {difficulty}}}]}}""",
                "description": "选择题默认生成模板",
                "is_active": True,
            })
            pp("创建 choice 模板", r)

        # ── Step 5: 生成练习题 ──
        print("\n" + "=" * 60)
        print("STEP 5: 生成练习题")
        
        r = await c.post("/api/v1/content/exercises/generate", json={
            "knowledge_point_id": kp_id,
            "exercise_type": "choice",
            "count": 3,
            "difficulty": 3,
        })
        pp("生成练习题", r)
        
        if r.status_code >= 400:
            print("  练习题生成失败，查看详细错误")
            return
        
        resource_id = r.json()["data"]["id"]
        print(f"  resource_id = {resource_id}")
        
        # ── Step 6: 查询练习题 ──
        print("\n" + "=" * 60)
        print("STEP 6: 查询练习题")
        
        # 6a: 按 resource_id 查询
        r = await c.get(f"/api/v1/content/exercises/{resource_id}")
        pp("按ID查询练习", r)
        
        # 6b: 按知识点查询
        r = await c.get(f"/api/v1/content/knowledge-points/{kp_id}/exercises")
        pp("按知识点查询练习", r)
        
        # 6c: 列表查询
        r = await c.get("/api/v1/content/exercises", params={
            "exercise_type": "choice",
            "limit": 10,
        })
        pp("列表查询练习", r)
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
