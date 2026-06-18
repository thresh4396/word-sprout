"""
「词芽」复习引擎
SM-2 间隔重复算法 + 选择题干扰项生成
"""

import random
from datetime import date, timedelta
from config import SM2_DEFAULT_EF, SM2_MIN_EF, SM2_MAX_EF, MASTERY_CORRECT_MIN, MASTERY_RATIO, MASTERY_INTERVAL_MIN, MASTERY_TIERS


def calculate_next_review(phrase, quality):
    """
    SM-2 算法核心
    quality: 0-5
      0 = 完全不记得
      1 = 答错但看到答案有印象
      2 = 答错但答案很熟悉
      3 = 答对但很费劲
      4 = 答对稍作犹豫
      5 = 完全不假思索
    返回更新后的词组数据
    """
    ef = phrase.get("ef", SM2_DEFAULT_EF)
    interval = phrase.get("interval_days", 0)

    if quality >= 3:
        # 正确：计算新间隔
        if interval == 0:
            interval = 1  # 首次：1天后
        elif interval == 1:
            interval = 3  # 第二次：3天后
        else:
            interval = int(interval * ef)

        # 更新 EF
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ef = max(SM2_MIN_EF, min(SM2_MAX_EF, ef))
    else:
        # 失败：重置间隔并降低 EF（标准 SM-2）
        interval = 1
        ef = ef - 0.2
        ef = max(SM2_MIN_EF, ef)

    phrase["ef"] = round(ef, 2)
    phrase["interval_days"] = interval
    phrase["review_count"] = phrase.get("review_count", 0) + 1
    if quality >= 3:
        phrase["correct_count"] = phrase.get("correct_count", 0) + 1

    # 连续正确/错误追踪
    consec_correct = phrase.get("consecutive_correct", 0)
    consec_wrong = phrase.get("consecutive_wrong", 0)
    if quality >= 3:
        consec_correct += 1
        consec_wrong = 0
    else:
        consec_wrong += 1
        consec_correct = 0
    phrase["consecutive_correct"] = consec_correct
    phrase["consecutive_wrong"] = consec_wrong

    phrase["last_reviewed"] = date.today().isoformat()
    phrase["next_review"] = (date.today() + timedelta(days=interval)).isoformat()

    # 判断掌握（需要：足够次数 + 足够正确率 + 足够间隔）
    rc = phrase["correct_count"]
    cc = phrase["review_count"]
    phrase["mastered"] = (
        rc >= MASTERY_CORRECT_MIN
        and cc >= MASTERY_CORRECT_MIN
        and (rc / cc) >= MASTERY_RATIO
        and interval >= MASTERY_INTERVAL_MIN
    )

    return phrase


def get_due_phrases(phrases):
    """获取今日需要复习的词组"""
    today = date.today().isoformat()
    due = [p for p in phrases if p.get("next_review", today) <= today]
    # 按 EF 升序（弱项优先）
    due.sort(key=lambda p: p.get("ef", SM2_DEFAULT_EF))
    return due


def get_due_count(phrases):
    return len(get_due_phrases(phrases))


def get_mastery_rate(phrases):
    """计算掌握率（tree 等级占比）"""
    if not phrases:
        return 0.0
    mastered = sum(1 for p in phrases if get_mastery_level(p) == "tree")
    return mastered / len(phrases)


def get_mastery_level(phrase):
    """
    返回掌握等级
    - "seedling": review_count < 2
    - "sprout": review_count >= 2 且未达到 tree 条件
    - "tree": review_count >= 5, correct_rate >= 80%, interval >= 21 天
    """
    rc = phrase.get("review_count", 0)
    if rc < 2:
        return "seedling"

    cc = phrase.get("correct_count", 0)
    if rc >= MASTERY_CORRECT_MIN and cc >= MASTERY_CORRECT_MIN:
        rate = cc / rc if rc > 0 else 0
        interval = phrase.get("interval_days", 0)
        if rate >= MASTERY_RATIO and interval >= MASTERY_INTERVAL_MIN:
            return "tree"

    return "sprout"


def get_mastery_tier_info(phrase):
    """返回给定词组的掌握等级信息 dict"""
    level = get_mastery_level(phrase)
    return MASTERY_TIERS[level]


def generate_quiz_options(correct_phrase, all_phrases, n=4):
    """
    生成选择题选项
    返回 (options_list, correct_index)
    """
    others = [p for p in all_phrases if p["id"] != correct_phrase["id"]]
    # 尽量选不同含义的干扰项
    random.shuffle(others)
    distractors = others[:n - 1]
    options = [correct_phrase["meaning"]] + [d["meaning"] for d in distractors]
    # 确保无重复
    seen = set()
    unique_options = []
    for o in options:
        if o not in seen:
            seen.add(o)
            unique_options.append(o)
    # 如果去重后不够 n 个，补空
    while len(unique_options) < n:
        unique_options.append("—")
    options = unique_options[:n]
    random.shuffle(options)
    correct_index = options.index(correct_phrase["meaning"])
    return options, correct_index
