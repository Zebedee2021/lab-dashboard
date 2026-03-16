"""
核心数据处理引擎
将飞书原始JSON解析为结构化的项目/人员/风险/时间线数据
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "..")


def load_config():
    config_path = os.path.join(SCRIPT_DIR, "project_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_raw_data():
    data_path = os.path.join(ROOT_DIR, "data", "raw", "feishu_report_data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_week_id(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def get_week_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


# ─── 项目名称归一化 ─────────────────────────────────────────────

def build_alias_map(config):
    """构建 别名→项目ID 的映射表"""
    alias_map = {}
    for proj_id, proj_info in config.get("projects", {}).items():
        for alias in proj_info.get("aliases", []):
            alias_map[alias.lower()] = proj_id
        alias_map[proj_info["name"].lower()] = proj_id
    return alias_map


def normalize_project_name(raw_name, alias_map, config):
    """将原始项目名称归一化为标准项目ID"""
    raw_lower = raw_name.lower().strip()
    # 精确匹配
    for alias, proj_id in alias_map.items():
        if alias in raw_lower or raw_lower in alias:
            return proj_id
    # 模糊匹配（取前4字）
    for alias, proj_id in alias_map.items():
        if len(alias) >= 2 and alias[:2] in raw_lower:
            return proj_id
    return None


def match_text_to_projects(text, alias_map, config):
    """从文本中匹配关联的项目"""
    matched = set()
    text_lower = text.lower()
    for alias, proj_id in alias_map.items():
        if len(alias) >= 2 and alias in text_lower:
            matched.add(proj_id)
    return list(matched)


# ─── 管理层报告解析 ───────────────────────────────────────────

def parse_manager_report_projects(work_text):
    """从管理层'本周工作'字段解析各项目信息"""
    projects = []
    # 按 "项目名称：" 或 "项目名称:" 分割
    pattern = r'(?:\d+[\.\、\s]*)?项目名称[：:]'
    parts = re.split(pattern, work_text)

    for part in parts[1:]:  # 跳过第一段（项目名称之前的内容）
        proj = extract_project_fields(part)
        if proj.get("name"):
            projects.append(proj)
    return projects


def extract_project_fields(text):
    """从单个项目段落中提取各字段"""
    markers = [
        ("name", r'^([^关总核本下风]{1,30})'),
        ("deadline", r'关键节点[：:](.+?)(?=总体|核心|本周|下周|风险|$)'),
        ("status", r'总体状态[：:](.+?)(?=核心|本周|下周|风险|$)'),
        ("members", r'核心人员[：:](.+?)(?=本周|下周|风险|$)'),
        ("progress", r'本周核心进展[：:](.+?)(?=下周|风险|$)'),
        ("next_plan", r'下周关键计划[：:](.+?)(?=风险|$)'),
        ("risks", r'风险与问题[：:](.+?)$'),
    ]
    result = {}
    for key, pat in markers:
        match = re.search(pat, text, re.DOTALL)
        if match:
            val = match.group(1).strip().rstrip("。，、")
            if key == "name":
                # 清理项目名称中的多余字符
                val = re.sub(r'[关键节点总体状态].*', '', val).strip().rstrip("，。")
            result[key] = val

    # 将进展和计划拆分为列表
    for list_key in ("progress", "next_plan", "risks"):
        if list_key in result:
            items = re.split(r'[；;。\n]|(?:\(\d+\))|(?:（\d+）)', result[list_key])
            result[list_key] = [i.strip() for i in items if i.strip()]

    # 成员拆分为列表
    if "members" in result:
        result["members"] = [m.strip() for m in re.split(r'[，,、]', result["members"]) if m.strip()]

    return result


# ─── 学生报告解析 ─────────────────────────────────────────────

def parse_student_report(form_contents):
    """解析学生周报的表单字段"""
    fields = {}
    for fc in form_contents:
        name = fc.get("field_name", "").strip()
        value = fc.get("field_value", "").strip()
        if "当前任务" in name:
            fields["current_tasks"] = value
        elif "本周工作" in name:
            fields["this_week_work"] = value
        elif "下周计划" in name:
            fields["next_plan"] = value
        elif "协调" in name or "帮助" in name:
            fields["need_help"] = value
    return fields


def parse_manager_form(form_contents):
    """解析管理层周报的表单字段"""
    fields = {}
    for fc in form_contents:
        name = fc.get("field_name", "").strip()
        value = fc.get("field_value", "").strip()
        if "概况" in name:
            fields["overview"] = value
        elif "本周工作" in name or "本周" in name and "工作" in name:
            fields["work"] = value
        elif "下周计划" in name or "计划" in name:
            fields["next_plan"] = value
        elif "协调" in name or "帮助" in name:
            fields["need_help"] = value
    return fields


# ─── 状态评级 ─────────────────────────────────────────────────

def assess_status_level(status_text, risks):
    """根据状态和风险评估等级"""
    risk_text = " ".join(risks) if isinstance(risks, list) else str(risks)
    combined = (status_text + " " + risk_text).lower()

    red_keywords = ["严重", "失败", "停滞", "阻塞", "瓶颈", "不佳", "延期"]
    yellow_keywords = ["风险", "不确定", "待", "优化", "关键期", "收尾", "采购"]
    green_keywords = ["完成", "正常", "顺利", "已交付"]

    for kw in red_keywords:
        if kw in combined:
            return "red"
    for kw in yellow_keywords:
        if kw in combined:
            return "yellow"
    for kw in green_keywords:
        if kw in combined:
            return "green"
    return "yellow"


# ─── 主处理流程 ───────────────────────────────────────────────

def process_all(raw_data, config):
    alias_map = build_alias_map(config)
    manager_rules = set(config.get("manager_rules", []))
    student_rules = set(config.get("student_rules", []))
    projects_config = config.get("projects", {})

    # 收集器
    project_snapshots = {}  # proj_id → [snapshots]
    people_data = {}        # name → person_info
    risk_registry = {}      # risk_key → risk_info
    week_data = {}          # week_id → week_info

    for report in raw_data:
        reporter = report.get("from_user_name", "")
        rule_name = report.get("rule_name", "")
        commit_time = report.get("commit_time", 0)
        week_id = get_week_id(commit_time)
        week_date = get_week_date(commit_time)
        dept = report.get("department_name", "")
        form_contents = report.get("form_contents", [])

        # ─── 人员数据收集 ───
        if reporter not in people_data:
            role = "manager"
            if reporter in config.get("roles", {}).get("students", []):
                role = "student"
            elif reporter in config.get("roles", {}).get("staff", []):
                role = "staff"
            people_data[reporter] = {
                "name": reporter,
                "department": dept,
                "role": role,
                "related_projects": set(),
                "reports": [],
            }

        # ─── 周数据收集 ───
        if week_id not in week_data:
            # 计算周起止日期
            dt = datetime.fromtimestamp(commit_time)
            week_start = dt - timedelta(days=dt.weekday())
            week_end = week_start + timedelta(days=6)
            week_data[week_id] = {
                "week_id": week_id,
                "date_range": f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}",
                "report_count": 0,
                "reporters": [],
            }
        week_data[week_id]["report_count"] += 1
        if reporter not in week_data[week_id]["reporters"]:
            week_data[week_id]["reporters"].append(reporter)

        # ─── 管理层报告处理 ───
        if rule_name in manager_rules:
            fields = parse_manager_form(form_contents)
            work_text = fields.get("work", "")

            # 解析项目
            parsed_projects = parse_manager_report_projects(work_text)
            for proj in parsed_projects:
                proj_name = proj.get("name", "")
                proj_id = normalize_project_name(proj_name, alias_map, config)
                if not proj_id:
                    continue

                if proj_id not in project_snapshots:
                    project_snapshots[proj_id] = []

                status = proj.get("status", "")
                risks = proj.get("risks", [])
                snapshot = {
                    "week": week_id,
                    "date": week_date,
                    "source_reporter": reporter,
                    "status": status,
                    "progress": proj.get("progress", []),
                    "next_plan": proj.get("next_plan", []),
                    "risks": risks,
                    "members": proj.get("members", []),
                    "status_level": assess_status_level(status, risks),
                }
                project_snapshots[proj_id].append(snapshot)

                # 风险收集
                for risk_text in (risks if isinstance(risks, list) else [risks]):
                    if risk_text and len(risk_text) > 5:
                        risk_key = f"{proj_id}:{risk_text[:20]}"
                        if risk_key not in risk_registry:
                            severity = "high" if any(kw in risk_text for kw in ["瓶颈", "不佳", "严重"]) else "medium"
                            risk_registry[risk_key] = {
                                "project_id": proj_id,
                                "project_name": projects_config.get(proj_id, {}).get("name", proj_name),
                                "description": risk_text,
                                "category": "技术风险" if "技术" in risk_text else "管理风险",
                                "severity": severity,
                                "first_reported": week_id,
                                "last_reported": week_id,
                                "status": "open",
                                "history": [{"week": week_id, "description": risk_text}],
                            }
                        else:
                            risk_registry[risk_key]["last_reported"] = week_id
                            risk_registry[risk_key]["history"].append(
                                {"week": week_id, "description": risk_text}
                            )

                # 人员-项目关联
                for member in proj.get("members", []):
                    if member in people_data:
                        people_data[member]["related_projects"].add(proj_id)

            # 管理层个人报告
            people_data[reporter]["reports"].append({
                "week": week_id,
                "date": week_date,
                "rule_name": rule_name,
                "overview": fields.get("overview", ""),
                "next_plan": fields.get("next_plan", ""),
                "need_help": fields.get("need_help", ""),
                "type": "manager",
            })

        # ─── 学生报告处理 ───
        elif rule_name in student_rules:
            fields = parse_student_report(form_contents)
            all_text = " ".join(fields.values())
            matched_projects = match_text_to_projects(all_text, alias_map, config)

            for proj_id in matched_projects:
                people_data[reporter]["related_projects"].add(proj_id)

                # 将学生工作关联到项目
                if proj_id not in project_snapshots:
                    project_snapshots[proj_id] = []

            people_data[reporter]["reports"].append({
                "week": week_id,
                "date": week_date,
                "rule_name": rule_name,
                "current_tasks": fields.get("current_tasks", ""),
                "this_week_work": fields.get("this_week_work", ""),
                "next_plan": fields.get("next_plan", ""),
                "need_help": fields.get("need_help", ""),
                "related_projects": matched_projects,
                "type": "student",
            })

    # ─── 组装输出 ───

    # 1. projects.json
    projects_output = []
    for proj_id, proj_conf in projects_config.items():
        snapshots = project_snapshots.get(proj_id, [])
        snapshots.sort(key=lambda x: x["week"])

        # 收集所有成员
        all_members = set()
        for s in snapshots:
            all_members.update(s.get("members", []))
        # 也从人员数据中反查
        for pname, pinfo in people_data.items():
            if proj_id in pinfo["related_projects"]:
                all_members.add(pname)

        latest_status = snapshots[-1]["status"] if snapshots else ""
        latest_level = snapshots[-1]["status_level"] if snapshots else "gray"
        latest_risks = snapshots[-1].get("risks", []) if snapshots else []

        # 关联的学生周报
        student_reports = []
        for pname, pinfo in people_data.items():
            if proj_id in pinfo["related_projects"] and pinfo["role"] == "student":
                for r in pinfo["reports"]:
                    if r.get("type") == "student":
                        student_reports.append({
                            "name": pname,
                            "week": r["week"],
                            "date": r["date"],
                            "work": r.get("this_week_work", ""),
                            "plan": r.get("next_plan", ""),
                        })

        projects_output.append({
            "id": proj_id,
            "name": proj_conf["name"],
            "category": proj_conf.get("category", ""),
            "deadline": proj_conf.get("deadline", ""),
            "status": latest_status,
            "status_level": latest_level,
            "core_members": sorted(all_members),
            "weekly_snapshots": snapshots,
            "latest_risks": latest_risks,
            "student_reports": sorted(student_reports, key=lambda x: x["week"]),
        })

    # 2. people.json
    people_output = []
    for pname, pinfo in people_data.items():
        people_output.append({
            "name": pinfo["name"],
            "department": pinfo["department"],
            "role": pinfo["role"],
            "related_projects": sorted(pinfo["related_projects"]),
            "reports": sorted(pinfo["reports"], key=lambda x: x["date"]),
            "report_count": len(pinfo["reports"]),
        })
    people_output.sort(key=lambda x: ({"manager": 0, "staff": 1, "student": 2}.get(x["role"], 3), x["name"]))

    # 3. risks.json
    risks_output = list(risk_registry.values())
    for r in risks_output:
        weeks = [h["week"] for h in r["history"]]
        r["trend"] = "unchanged" if len(set(weeks)) <= 1 else "persistent"
    risks_output.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))

    # 4. timeline.json
    timeline_output = sorted(week_data.values(), key=lambda x: x["week_id"])

    # 5. feedback.json (初始为已有的反馈数据)
    feedback_output = load_existing_feedback()

    # Meta
    meta = {
        "generated_at": datetime.now().isoformat(),
        "total_reports": len(raw_data),
        "total_projects": len(projects_output),
        "total_people": len(people_output),
        "week_range": [timeline_output[0]["week_id"], timeline_output[-1]["week_id"]] if timeline_output else [],
    }

    return {
        "projects": {"projects": projects_output, "meta": meta},
        "people": {"people": people_output, "meta": meta},
        "risks": {"risks": risks_output, "meta": meta},
        "timeline": {"weeks": timeline_output, "meta": meta},
        "feedback": feedback_output,
    }


def load_existing_feedback():
    """加载已有的反馈数据"""
    feedback_path = os.path.join(ROOT_DIR, "data", "processed", "feedback.json")
    if os.path.exists(feedback_path):
        with open(feedback_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 初始反馈数据（从之前的截图记录）
    return {
        "feedbacks": [
            {
                "from": "周治国",
                "to": "周学华",
                "date": "2026-03-15",
                "target_report_week": "2026-W11",
                "items": [
                    {"project": "启元-红外项目", "content": "及时汇总及发下资料，不要像上次，最后才看到材料", "type": "action_required"},
                    {"project": "国重项目(微电网故障诊断)", "content": "怎么回事？风险这么高？？训练系统技术方案复杂，实现难度可能被低估；论文、软著、专利等不符合预期进度要求", "type": "concern"},
                    {"project": "150W IC采购项目", "content": "建议采用具体数据，哪些未到？", "type": "improvement"},
                    {"project": "智能机舱", "content": "这个项目，后来合同准备怎么处理？我们做什么？怎么验收？什么都不确定就先别接。", "type": "decision_needed"},
                    {"project": "整体", "content": "提高汇报频次，现在罗列了细节，缺乏整体把控，项目全局观需要培养", "type": "overall"},
                    {"project": "整体", "content": "本周把25年工作复盘一下，不然今年又会陷入泥沼", "type": "action_required"},
                ],
            }
        ]
    }


def save_outputs(results):
    output_dir = os.path.join(ROOT_DIR, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    for name, data in results.items():
        path = os.path.join(output_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] {path} ({len(json.dumps(data, ensure_ascii=False))} bytes)")


def main():
    print("=" * 60)
    print("数据处理引擎")
    print("=" * 60)

    config = load_config()
    print(f"[OK] 加载配置: {len(config.get('projects', {}))} 个项目定义")

    raw_data = load_raw_data()
    print(f"[OK] 加载原始数据: {len(raw_data)} 条记录")

    results = process_all(raw_data, config)

    print(f"\n处理结果:")
    print(f"  项目数: {len(results['projects']['projects'])}")
    print(f"  人员数: {len(results['people']['people'])}")
    print(f"  风险数: {len(results['risks']['risks'])}")
    print(f"  周数据: {len(results['timeline']['weeks'])} 周")

    save_outputs(results)
    print("\n[DONE] 所有数据处理完成")


if __name__ == "__main__":
    main()
