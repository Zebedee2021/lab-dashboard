"""
飞书API数据拉取脚本
凭据从环境变量读取，支持时间范围参数
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

BASE_URL = "https://open.feishu.cn/open-apis"


def get_tenant_access_token(app_id, app_secret):
    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    if data.get("code") == 0:
        return data["tenant_access_token"]
    print(f"[ERROR] 获取token失败: {data}", file=sys.stderr)
    return None


def query_report_tasks(token, start_time, end_time, rule_id=None, page_size=20):
    url = f"{BASE_URL}/report/v1/tasks/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    all_items = []
    page_token = ""
    while True:
        payload = {
            "commit_start_time": start_time,
            "commit_end_time": end_time,
            "page_token": page_token,
            "page_size": page_size,
        }
        if rule_id:
            payload["rule_id"] = rule_id
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            all_items.extend(items)
            if data.get("data", {}).get("has_more"):
                page_token = data["data"].get("page_token", "")
            else:
                break
        else:
            print(f"[ERROR] 查询失败: {data}", file=sys.stderr)
            break
    return all_items


def main():
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("[ERROR] 请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET", file=sys.stderr)
        sys.exit(1)

    token = get_tenant_access_token(app_id, app_secret)
    if not token:
        sys.exit(1)

    # 默认拉取最近60天
    days = int(os.environ.get("FETCH_DAYS", "60"))
    now = int(time.time())
    start = now - days * 86400

    print(f"[INFO] 拉取 {days} 天数据: {datetime.fromtimestamp(start)} ~ {datetime.fromtimestamp(now)}")
    items = query_report_tasks(token, start, now)
    print(f"[INFO] 获取到 {len(items)} 条记录")

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "feishu_report_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[OK] 数据已保存: {output_file}")


if __name__ == "__main__":
    main()
