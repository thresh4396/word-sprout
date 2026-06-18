"""
「词芽」AI API 客户端
兼容 OpenAI 格式，支持多厂商预设
"""

import json
import urllib.request
import urllib.error
from config import API_PRESETS


def _build_chat_request(api_key, base_url, model, messages, temperature=0.8, max_tokens=4096, json_mode=False):
    """构造 HTTP 请求"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    body_dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body_dict["response_format"] = {"type": "json_object"}
    body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    return req


def generate_content(phrases, content_type="dialogue", provider="deepseek",
                     api_key="", base_url="", model="", temperature=0.8,
                     word_count=None):
    """
    调用 AI 生成对话或文章
    word_count: "short" (~200词) | "medium" (~350词) | "long" (~500词)
    """
    preset = API_PRESETS.get(provider, API_PRESETS["custom"])
    if not base_url:
        base_url = preset.get("base_url", "")
    if not model:
        model = preset.get("default_model", "")
    if not api_key:
        raise ValueError("请先在设置中填入 API Key")

    phrase_list = "\n".join(
        f"- {p['phrase']}（{p['meaning']}）{' 例句：' + p.get('example', '') if p.get('example') else ''}"
        for p in phrases
    )

    if content_type == "article":
        system_prompt = _article_system_prompt(word_count)
    else:
        system_prompt = _dialogue_system_prompt()

    user_prompt = f"请用以下英语词组生成{'文章' if content_type == 'article' else '对话'}：\n\n{phrase_list}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 文章需要更多输出 token（段落 + 5 道阅读理解题）
    tokens = 8192 if content_type == "article" else 4096
    req = _build_chat_request(api_key, base_url, model, messages, temperature, max_tokens=tokens, json_mode=True)

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API 请求失败 ({e.code}): {error_body[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"请求异常: {str(e)}")

    content = data["choices"][0]["message"]["content"]
    result = _parse_json_response(content)
    result["content_type"] = content_type
    return result


def generate_dialogue(phrases, provider="deepseek", api_key="",
                      base_url="", model="", temperature=0.8):
    """兼容旧接口"""
    return generate_content(phrases, "dialogue", provider, api_key, base_url, model, temperature)


def _dialogue_system_prompt():
    return """你是一个英语教学助手，专门设计高考/四六级风格的阅读理解题。

你需要用给定的英语词组生成一段自然流畅的英语对话，并配套标准阅读理解题。

## 对话要求
1. 场景贴近日常生活或工作场景，对话人数为 2 人（标记为 A 和 B）
2. 对话篇幅约 10-15 轮，内容有深度、有观点碰撞或情节推进
3. 每个目标词组至少出现一次，用完后即可自然流转
4. 对话整体像一篇完整的微型阅读篇章，不是零散的闲聊

## 阅读理解题要求（5 道，每道 4 选 1）
请设计以下 5 种类型的题目：
1. **主旨大意题** 2. **细节理解题** 3. **推理判断题** 4. **词义猜测题**（考点必须是目标词组之一）5. **观点态度题**
每道题的 4 个选项要有干扰性。
每道题附带 explanation 字段，用 1-2 句中文简要解析正确答案的理由。

## 输出格式（严格 JSON）
{
  "title": "对话标题（英文）",
  "dialogue": [{"speaker": "A", "text": "..."}, {"speaker": "B", "text": "..."}],
  "comprehension_questions": [
    {"type": "main_idea", "question": "...", "options": ["A","B","C","D"], "answer": 0, "explanation": "解析..."},
    ...
  ],
  "blanks": [{"speaker_idx": 0, "phrase": "完整词组原文"}, ...]
}
blanks 覆盖至少一半的目标词组。"""


def _article_system_prompt(word_count=None):
    if isinstance(word_count, int):
        length_guide = f"篇幅约 {word_count} 词，段落数自行合理安排"
    elif word_count == "short":
        length_guide = "篇幅约 180-250 词，分 2-3 个自然段"
    elif word_count == "long":
        length_guide = "篇幅约 450-600 词，分 4-6 个自然段，内容要有深度"
    else:
        length_guide = "篇幅约 300-400 词，分 3-5 个自然段"

    return f"""你是一个英语教学助手，擅长用目标词汇撰写可读性强的英语短文。

你需要用给定的英语词组写一篇结构完整的英语文章，并配套阅读理解题。

## 文章要求
1. 题材可以是：观点论述、经历分享、科普说明、书评/影评等
2. {length_guide}
3. 每个目标词组至少出现一次，使用自然不刻意
4. 文章有明确的标题和段落结构
5. 语言难度适合高考/四级水平
6. 文章要有实质内容，不要空洞地堆砌词组

## 阅读理解题要求（5 道，每道 4 选 1）
1. **主旨大意题** 2. **细节理解题** 3. **推理判断题** 4. **词义猜测题** 5. **观点态度题**
每道题附带 explanation 字段，用 1-2 句中文简要解析正确答案的理由。

## 输出格式（严格 JSON）
{{
  "title": "文章标题（英文）",
  "paragraphs": ["段落1全文...", "段落2全文...", "段落3全文..."],
  "comprehension_questions": [
    {{"type": "main_idea", "question": "...", "options": ["A","B","C","D"], "answer": 0, "explanation": "解析..."}},
    ...
  ],
  "blanks": [{{"paragraph_idx": 0, "phrase": "完整词组原文"}}, ...]
}}
blanks 覆盖至少一半的目标词组，paragraph_idx 从 0 开始计数。"""


def _parse_json_response(content):
    """鲁棒解析 AI 返回的 JSON，处理各种常见格式问题"""
    import re
    original = content
    content = content.strip()

    # 1. 去掉 markdown 代码块 ```json ... ``` 或 ``` ... ```
    if content.startswith("```"):
        lines = content.split("\n")
        start = 1
        # 跳过可能的语言标识（如 ```json）
        end = -1 if lines[-1].strip() == "```" else len(lines)
        content = "\n".join(lines[start:end]).strip()

    # 2. 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 3. 用正则提取最外层 JSON 对象或数组
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            json_str = match.group()
            json_str = _repair_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    # 4. 全部失败：提供详细信息帮助排查
    # 截取原始响应供调试
    snippet = original[:800]
    raise RuntimeError(
        f"AI 返回格式异常，无法解析为 JSON。\n\n"
        f"── 原始返回（前 800 字）──\n{snippet}\n"
        f"── 请检查 API 设置或重试 ──"
    )


def _repair_json(json_str):
    """尝试修复 AI 生成 JSON 时的常见错误"""
    import re

    # 1. 移除 BOM / 零宽字符
    json_str = json_str.replace('﻿', '').replace('​', '')

    # 2. 移除尾随逗号（在 } 或 ] 前）
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    # 3. 移除注释（// 或 # 开头的行）
    json_str = re.sub(r'^\s*//.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'^\s*#.*$', '', json_str, flags=re.MULTILINE)

    # 4. 修复字符串内的裸换行符 → \\n
    json_str = _escape_inner_newlines(json_str)

    # 5. 尝试修复单引号 JSON：{'key': 'value'} → {"key": "value"}
    if "'" in json_str and '"' not in json_str:
        json_str = _fix_single_quotes(json_str)

    return json_str


def _escape_inner_newlines(text):
    """修复 JSON 字符串值内未转义的换行符"""
    import re
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\':
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch in ('\n', '\r'):
            result.append('\\n' if ch == '\n' else '\\r')
            continue
        result.append(ch)
    return ''.join(result)


def _fix_single_quotes(text):
    """将单引号 JSON 转为双引号 JSON"""
    # 策略：逐字符转换，跳过字符串内部的单引号
    import re
    result = []
    in_string = False  # 当前是否在双引号字符串内
    in_single = False  # 当前是否在单引号字符串内
    escape_next = False

    for i, ch in enumerate(text):
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\':
            result.append(ch)
            escape_next = True
            continue
        if ch == '"' and not in_single:
            # 双引号：切换状态
            in_string = not in_string
            result.append(ch)
            continue
        if ch == "'":
            if in_string:
                # 在双引号内部 → 保留为字面单引号
                result.append(ch)
            elif in_single:
                # 关闭单引号字符串
                in_single = False
                result.append('"')
            else:
                # 开启单引号字符串
                in_single = True
                result.append('"')
            continue
        result.append(ch)

    return ''.join(result)


def translate_text(text, provider="deepseek", api_key="", base_url="", model=""):
    """翻译英文文本为中文"""
    preset = API_PRESETS.get(provider, API_PRESETS["custom"])
    if not base_url:
        base_url = preset.get("base_url", "")
    if not model:
        model = preset.get("default_model", "")
    if not api_key:
        raise ValueError("请先在设置中填入 API Key")

    system_prompt = "你是一个专业翻译。把用户提供的英文翻译成流畅的中文。保持原文格式（段落、对话结构等）。只返回翻译结果，不要加任何解释。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请翻译以下英文为中文：\n\n{text}"},
    ]
    req = _build_chat_request(api_key, base_url, model, messages, temperature=0.3, max_tokens=4096)

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def test_api_connection(provider, api_key, base_url="", model=""):
    """测试 API 连接是否正常"""
    preset = API_PRESETS.get(provider, API_PRESETS["custom"])
    if not base_url:
        base_url = preset.get("base_url", "")
    if not model:
        model = preset.get("default_model", "")

    messages = [{"role": "user", "content": "Hello, respond with just 'OK'."}]
    req = _build_chat_request(api_key, base_url, model, messages, temperature=0)

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"]
