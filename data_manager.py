"""
「词芽」数据管理层
JSON 文件 CRUD + 与第一步同步
"""

import json
import os
import uuid
from datetime import datetime, date
from typing import Optional

from config import (
    DATA_DIR, PHRASES_FILE, REVIEW_LOG_FILE, DAILY_STATS_FILE,
    SETTINGS_FILE, DIALOGUES_FILE,
    DEFAULT_SETTINGS, API_PRESETS,
)


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(filepath, default=None):
    _ensure_data_dir()
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def _write_json(filepath, data):
    _ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def today_key():
    return date.today().isoformat()


def now_iso():
    return datetime.now().isoformat()


# ============================================================
# 词组 CRUD
# ============================================================

def get_phrases():
    return _read_json(PHRASES_FILE, [])


def save_phrases(phrases):
    _write_json(PHRASES_FILE, phrases)


def add_phrase(phrase_text, meaning, example="", tags=None):
    """添加一条新词组"""
    phrases = get_phrases()
    now = now_iso()
    today = today_key()
    p = {
        "id": uuid.uuid4().hex[:12],
        "phrase": phrase_text.strip(),
        "meaning": meaning.strip(),
        "example": example.strip(),
        "tags": tags or [],
        "created": now,
        "review_count": 0,
        "correct_count": 0,
        "last_reviewed": None,
        "next_review": today,  # 当天即可复习
        "ef": 2.5,
        "interval_days": 0,
        "mastered": False,
    }
    phrases.append(p)
    save_phrases(phrases)
    # 更新每日统计
    stats = get_daily_stats()
    td = stats.get(today, {})
    td["phrases_added"] = td.get("phrases_added", 0) + 1
    td["total_phrases_so_far"] = len(phrases)
    stats[today] = td
    save_daily_stats(stats)
    return p


def update_phrase(phrase_id, updates: dict):
    """更新词组字段"""
    phrases = get_phrases()
    for p in phrases:
        if p["id"] == phrase_id:
            p.update(updates)
            save_phrases(phrases)
            return p
    return None


def delete_phrase(phrase_id):
    """删除词组"""
    phrases = get_phrases()
    phrases = [p for p in phrases if p["id"] != phrase_id]
    save_phrases(phrases)


def get_phrase_by_id(phrase_id):
    phrases = get_phrases()
    for p in phrases:
        if p["id"] == phrase_id:
            return p
    return None


def get_all_tags():
    """获取所有标签，按使用频率排序"""
    phrases = get_phrases()
    tag_counts = {}
    for p in phrases:
        for t in p.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    return sorted(tag_counts.keys(), key=lambda t: -tag_counts[t])


# ============================================================
# 每日统计
# ============================================================

def get_daily_stats():
    return _read_json(DAILY_STATS_FILE, {})


def save_daily_stats(stats):
    _write_json(DAILY_STATS_FILE, stats)


def get_today_stats():
    stats = get_daily_stats()
    td = stats.get(today_key(), {})
    return {
        "phrases_added": td.get("phrases_added", 0),
        "phrases_reviewed": td.get("phrases_reviewed", 0),
        "review_sessions": td.get("review_sessions", 0),
        "dialogues_generated": td.get("dialogues_generated", 0),
        "total_phrases_so_far": td.get("total_phrases_so_far", len(get_phrases())),
    }


def record_review(phrase_id, quality):
    """记录一次复习结果并更新每日统计"""
    p = get_phrase_by_id(phrase_id)
    if not p:
        return
    today = today_key()
    p["review_count"] = p.get("review_count", 0) + 1
    if quality >= 3:
        p["correct_count"] = p.get("correct_count", 0) + 1
    p["last_reviewed"] = now_iso()
    update_phrase(phrase_id, p)

    # 更新每日统计
    stats = get_daily_stats()
    td = stats.get(today, {})
    td["phrases_reviewed"] = td.get("phrases_reviewed", 0) + 1
    stats[today] = td
    save_daily_stats(stats)


def record_review_session(mode, total, correct, duration_minutes=0):
    """记录一次完整的复习会话"""
    log_entry = {
        "date": today_key(),
        "mode": mode,
        "total": total,
        "correct": correct,
        "duration_minutes": duration_minutes,
        "timestamp": now_iso(),
    }
    log = _read_json(REVIEW_LOG_FILE, [])
    log.append(log_entry)
    _write_json(REVIEW_LOG_FILE, log)

    # 更新每日统计中的会话数
    stats = get_daily_stats()
    td = stats.get(today_key(), {})
    td["review_sessions"] = td.get("review_sessions", 0) + 1
    stats[today_key()] = td
    save_daily_stats(stats)


# ============================================================
# 对话历史
# ============================================================

def get_dialogues():
    return _read_json(DIALOGUES_FILE, [])


def save_dialogue(dialogue_data):
    """保存生成的对话"""
    dialogues = get_dialogues()
    d = {
        "id": uuid.uuid4().hex[:12],
        "created": now_iso(),
        "date": today_key(),
        **dialogue_data,
    }
    dialogues.append(d)
    _write_json(DIALOGUES_FILE, dialogues)

    # 更新每日统计
    stats = get_daily_stats()
    td = stats.get(today_key(), {})
    td["dialogues_generated"] = td.get("dialogues_generated", 0) + 1
    stats[today_key()] = td
    save_daily_stats(stats)
    return d


def delete_dialogue(dialogue_id):
    dialogues = get_dialogues()
    dialogues = [d for d in dialogues if d["id"] != dialogue_id]
    _write_json(DIALOGUES_FILE, dialogues)


# ============================================================
# 设置
# ============================================================

def get_settings():
    s = _read_json(SETTINGS_FILE, {})
    if not s:
        s = dict(DEFAULT_SETTINGS)
        save_settings(s)
    # 合并默认值（新增字段可能有默认值但文件中没有）
    for k, v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v
    return s


def save_settings(settings):
    _write_json(SETTINGS_FILE, settings)


# ============================================================
# 与第一步同步
# ============================================================

def sync_to_first_step():
    """将今日词芽数据写入第一步的 daily_log.json"""
    settings = get_settings()
    if not settings.get("sync_enabled", True):
        return

    # 解析路径
    sync_path = settings.get("first_step_data_path", "")
    if not sync_path:
        # 自动检测同级目录
        auto_path = os.path.join(os.path.dirname(DATA_DIR), "first-step", "data")
        if os.path.isdir(auto_path):
            sync_path = auto_path
        else:
            return  # 没有可同步的目标

    daily_log_path = os.path.join(sync_path, "daily_log.json")
    if not os.path.isfile(daily_log_path):
        return

    try:
        with open(daily_log_path, "r", encoding="utf-8") as f:
            daily_log = json.load(f)
    except (json.JSONDecodeError, IOError):
        daily_log = {}

    today = today_key()
    td = daily_log.get(today, {})
    stats = get_today_stats()
    td["vocab_added"] = stats["phrases_added"]
    td["vocab_reviewed"] = stats["phrases_reviewed"]
    td["vocab_total"] = stats["total_phrases_so_far"]
    td["vocab_dialogues"] = stats["dialogues_generated"]
    daily_log[today] = td

    with open(daily_log_path, "w", encoding="utf-8") as f:
        json.dump(daily_log, f, ensure_ascii=False, indent=2)


# ============================================================
# 导出
# ============================================================

def export_json(output_path):
    """导出全部词组为 JSON"""
    phrases = get_phrases()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phrases, f, ensure_ascii=False, indent=2)


def export_csv(output_path):
    """导出全部词组为 CSV"""
    import csv
    phrases = get_phrases()
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["词组", "释义", "例句", "标签", "日期", "复习次数", "正确次数", "已掌握"])
        for p in phrases:
            writer.writerow([
                p["phrase"], p["meaning"], p.get("example", ""),
                ", ".join(p.get("tags", [])), p["created"][:10],
                p["review_count"], p["correct_count"],
                "是" if p.get("mastered") else "否",
            ])
