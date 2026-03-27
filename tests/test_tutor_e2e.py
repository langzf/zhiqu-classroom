"""AI Tutor 模块 e2e 测试（7 步）"""
import sys, jwt, datetime, json, requests

BASE = "http://localhost:8001/api/v1/tutor"

# 签发测试 token
def make_token(sub="019d2e52-0000-7000-8000-000000000001", role="student"):
    return jwt.encode(
        {"sub": sub, "role": role,
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)},
        "dev-secret-change-in-production", algorithm="HS256"
    )

TOKEN = make_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def step(n, desc, method, path, expected_status, body=None, check=None):
    url = f"{BASE}{path}"
    r = getattr(requests, method)(url, headers=HEADERS, json=body, timeout=10)
    ok = r.status_code == expected_status
    data = None
    try:
        data = r.json()
    except:
        pass
    status = "✅" if ok else "❌"
    print(f"  STEP {n}: {desc} => {r.status_code} (expect {expected_status}) {status}")
    if not ok:
        print(f"    Response: {r.text[:500]}")
    if check and data:
        check(data)
    return data

print("=" * 60)
print("AI Tutor E2E 测试")
print("=" * 60)

# STEP 1: 创建会话
conv_id = None
def check1(d):
    global conv_id
    conv_id = d.get("data", {}).get("id")
    print(f"    conversation_id = {conv_id}")

step(1, "创建会话", "post", "/conversations",
     200, body={"title": "测试数学对话", "scene": "free_chat"}, check=check1)

if not conv_id:
    print("无法继续，STEP 1 失败"); sys.exit(1)

# STEP 2: 获取会话列表
step(2, "会话列表", "get", "/conversations", 200)

# STEP 3: 获取单个会话
step(3, "获取会话详情", "get", f"/conversations/{conv_id}", 200)

# STEP 4: 发送消息
msg_data = None
def check4(d):
    global msg_data
    msg_data = d.get("data", {})
    # 兼容多种返回结构
    if "user_message" in msg_data:
        print(f"    user_msg_id = {msg_data['user_message'].get('id')}")
        print(f"    assistant_msg_id = {msg_data['assistant_message'].get('id')}")
    elif "messages" in msg_data:
        for m in msg_data["messages"]:
            print(f"    msg: role={m.get('role')}, id={m.get('id')}")
    else:
        print(f"    data keys: {list(msg_data.keys())}")

step(4, "发送消息", "post", f"/conversations/{conv_id}/messages",
     200, body={"content": "1+1等于几？"}, check=check4)

# STEP 5: 获取消息列表
step(5, "消息列表", "get", f"/conversations/{conv_id}/messages", 200)

# STEP 6: 更新会话（PATCH）
step(6, "更新会话(PATCH)", "patch", f"/conversations/{conv_id}",
     200, body={"title": "已更新的标题"})

# STEP 7: 归档会话（DELETE / close）
step(7, "归档会话(DELETE)", "delete", f"/conversations/{conv_id}", 200)

# 验证归档后状态
def check_archived(d):
    status_val = d.get("data", {}).get("status")
    print(f"    归档后 status = {status_val}")

step("7b", "确认归档状态", "get", f"/conversations/{conv_id}", 200, check=check_archived)

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
