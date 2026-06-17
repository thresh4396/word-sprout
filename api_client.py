"""
「词芽」AI API 客户端
兼容 OpenAI 格式，支持多厂商预设
"""

import json
import urllib.request
import urllib.error
from config import API_PRESETS


def _build_chat_request(api_key, base_url, model, messages, temperature=0.8):
    """构造 HTTP 请求"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    return req


def generate_dialogue(phrases, provider="deepseek", api_key="",
                      base_url="", model="", temperature=0.8):
    """
    调用 AI 生成对话

    phrases: [{"phrase": "...", "meaning": "..."}, ...]
    返回: {
        "title": "对话标题",
        "dialogue": [{"speaker": "A", "text": "..."}, ...],
        "comprehension_questions": [{"question": "...", "options": [...], "answer": 0}, ...],
        "blanks": [{"speaker_idx": 0, "answer": "..."}, ...]
    }
    """
    # 获取厂商预设
    preset = API_PRESETS.get(provider, API_PRESETS["custom"])
    if not base_url:
        base_url = preset.get("base_url", "")
    if not model:
        model = preset.get("default_model", "")
    if not api_key:
        raise ValueError("请先在设置中填入 API Key")

    # 构建词组列表
    phrase_list = "\n".join(
        f"- {p['phrase']}（{p['meaning']}）{' 例句：' + p.get('example', '') if p.get('example') else ''}"
        for p in phrases
    )

    # 系统提示词
    system_prompt = """你是一个英语教学助手，专门设计高考/四六级风格的阅读理解题。

你需要用给定的英语词组生成一段自然流畅的英语对话，并配套标准阅读理解题。

## 对话要求
1. 场景贴近日常生活或工作场景，对话人数为 2 人（标记为 A 和 B）
2. 对话篇幅约 10-15 轮，内容有深度、有观点碰撞或情节推进
3. 每个目标词组至少出现一次，用完后即可自然流转
4. 对话整体像一篇完整的微型阅读篇章，不是零散的闲聊

## 阅读理解题要求（5 道，每道 4 选 1）
请设计以下 5 种类型的题目，覆盖不同能力维度：

1. **主旨大意题**：这段对话主要在讨论什么？
2. **细节理解题**：根据对话内容，某个具体事实是什么？
3. **推理判断题**：从对话中可以推断出什么？
4. **词义猜测题**：对话中某个词组/表达最可能是什么意思？（考点必须是你给出的目标词组之一）
5. **观点态度题**：说话者 A 或 B 对某事的看法/态度是什么？

每道题的 4 个选项要有干扰性（错误选项看起来也要合理），不要出现明显不相关的选项。

## 输出格式
请严格按以下 JSON 格式返回，不要包含任何其他文字：
{
  "title": "对话场景标题（英文）",
  "dialogue": [
    {"speaker": "A", "text": "..."},
    {"speaker": "B", "text": "..."}
  ],
  "comprehension_questions": [
    {
      "type": "main_idea",
      "question": "What is the conversation mainly about?",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": 0
    },
    {
      "type": "detail",
      "question": "细节理解题...",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": 0
    },
    {
      "type": "inference",
      "question": "推理判断题...",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": 0
    },
    {
      "type": "vocabulary",
      "question": "词义猜测题...",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": 0
    },
    {
      "type": "attitude",
      "question": "观点态度题...",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": 0
    }
  ],
  "blanks": [
    {"speaker_idx": 0, "phrase": "被挖空的词组原文"},
    {"speaker_idx": 3, "phrase": "被挖空的词组原文"}
  ]
}

blanks 数组中的每一项代表对话中一句话里包含一个需要被挖空的目标词组，请覆盖至少一半的目标词组。"""

    user_prompt = f"""请用以下英语词组生成对话：

{phrase_list}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    req = _build_chat_request(api_key, base_url, model, messages, temperature)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API 请求失败 ({e.code}): {error_body[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"请求异常: {str(e)}")

    # 解析响应
    content = data["choices"][0]["message"]["content"]

    # 尝试提取 JSON（有些模型会在 JSON 外包裹 markdown）
    content = content.strip()
    if content.startswith("```"):
        # 去掉 markdown 代码块标记
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试用正则提取 JSON 块
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise RuntimeError(f"AI 返回格式异常，无法解析为 JSON。原始内容:\n{content[:500]}")

    return result


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
