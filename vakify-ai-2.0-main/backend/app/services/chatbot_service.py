import json
import random
import re
from urllib.parse import quote_plus
import os

from app.services.openai_service import chatgpt_json, chatgpt_text, generate_image_data_url, openai_json_schema
from app.services.admin_workspace import DEFAULT_CHATBOT_PROMPT, get_chatbot_config
from urllib.parse import quote


def _fallback_response(question: str, style: str) -> str:
    topic = question.strip().rstrip("?") or "that topic"
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9+#-]{2,}", topic) if w.lower() not in {"what", "how", "can", "for", "and", "the", "with", "java", "does"}]
    focus = words[0] if words else "the idea"

    style_hint = {
        "visual": "I can also turn it into a diagram or a step map if you want.",
        "auditory": "I can explain it in a more conversational way if that helps.",
        "kinesthetic": "I can give you a hands-on example or quick practice task too.",
    }.get(style, "I can also show an example or a practice task if you want.")

    return (
        f"{topic} is mainly about understanding {focus} and using it in the right place. "
        f"The simplest way to approach it is to break the idea into small pieces, test one part at a time, "
        f"and check the edge cases before you move on. "
        f"For a real project, that usually means writing a small example, running it, and then improving it step by step. "
        f"{style_hint}"
    )


def _generate_chatgpt_explanation(question: str, style: str) -> str | None:
    style_prompt = {
        "visual": "Use visual wording when helpful, but keep the reply natural and conversational.",
        "auditory": "Use conversational spoken style with clear transitions and natural pacing.",
        "kinesthetic": "Use hands-on language with concrete implementation steps when useful.",
    }
    system_prompt = (
        "You are a friendly AI chat assistant for learners. Reply naturally in plain text. "
        "Do not force sections, headings, or templates. "
        "Be helpful, concise when possible, and expand only when the user needs depth."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Learning style: {style}\n"
        f"Instruction: {style_prompt.get(style, '')}\n"
        "Answer in a natural chat style."
    )
    return chatgpt_text(system_prompt, user_prompt, temperature=0.45)


def _topic_keywords(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#-]{2,}", topic)
    filtered = [w for w in words if w.lower() not in {"about", "explain", "learn", "with", "from", "that", "this"}]
    seen = set()
    result = []
    for word in filtered:
        low = word.lower()
        if low in seen:
            continue
        seen.add(low)
        result.append(word.capitalize())
        if len(result) == 5:
            break
    if not result:
        return ["Concept", "Flow", "Example", "Errors", "Practice"]
    return result


def _safe_label(text: str, max_len: int = 28) -> str:
    return (text or "Concept").replace("<", "").replace(">", "").strip()[:max_len]


def _title_case(text: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in text.split() if part)


def _fallback_visual_blueprint(topic: str) -> dict:
    clean_topic = _safe_label(topic or "Learning Topic", 42)
    concepts = _topic_keywords(topic)[:4]
    while len(concepts) < 4:
        concepts.append(f"Concept {len(concepts)+1}")
    return {
        "title": clean_topic,
        "concept_nodes": concepts,
        "flow_steps": ["Understand concept", "Follow process", "Apply in example", "Practice variations", "Review errors"],
        "radar_axes": ["Concept", "Flow", "Example", "Practice", "Revision"],
        "radar_scores": [78, 86, 82, 74, 80],
        "bar_labels": ["Basics", "Process", "Examples", "Practice"],
        "bar_values": [70, 84, 79, 76],
    }


def _sanitize_labels(raw: list, min_len: int, max_len: int, max_items: int, default_prefix: str) -> list[str]:
    out = []
    for item in raw or []:
        txt = _safe_label(str(item), max_len)
        if len(txt) < min_len:
            continue
        out.append(_title_case(txt))
        if len(out) >= max_items:
            break
    while len(out) < max_items:
        out.append(f"{default_prefix} {len(out)+1}")
    return out[:max_items]


def _sanitize_scores(raw: list, max_items: int, minimum: int = 40, maximum: int = 100) -> list[int]:
    out = []
    for item in raw or []:
        try:
            num = int(item)
        except (TypeError, ValueError):
            continue
        out.append(max(minimum, min(maximum, num)))
        if len(out) >= max_items:
            break
    while len(out) < max_items:
        out.append(70 + len(out) * 4)
    return out[:max_items]


def _generate_visual_blueprint(question: str, explanation: str) -> dict:
    system_prompt = (
        "You create visual learning blueprints. Return strict JSON only with keys: "
        "title, concept_nodes, flow_steps, radar_axes, radar_scores, bar_labels, bar_values. "
        "Use concise educational phrases. No markdown."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Answer summary: {(explanation or '')[:900]}\n\n"
        "Rules:\n"
        "- concept_nodes: 4 short conceptual nodes\n"
        "- flow_steps: 5 short step-by-step actions\n"
        "- radar_axes: exactly 5 dimensions\n"
        "- radar_scores: exactly 5 integers between 50 and 95\n"
        "- bar_labels: exactly 4 labels\n"
        "- bar_values: exactly 4 integers between 50 and 95"
    )
    payload = chatgpt_json(system_prompt, user_prompt, temperature=0.4) or {}
    fallback = _fallback_visual_blueprint(question)
    # If we have explanation text, derive better fallback step labels from it.
    if explanation:
        text_lines = [line.strip(" -•\t") for line in explanation.splitlines() if line.strip()]
        sentence_parts = []
        for line in text_lines:
            sentence_parts.extend([s.strip() for s in re.split(r"[.!?]", line) if s.strip()])
        derived_steps = []
        for part in sentence_parts:
            if len(part) < 8:
                continue
            derived_steps.append(_title_case(_safe_label(part, 24)))
            if len(derived_steps) == 5:
                break
        if len(derived_steps) >= 3:
            while len(derived_steps) < 5:
                derived_steps.append(f"Apply Step {len(derived_steps)+1}")
            fallback["flow_steps"] = derived_steps[:5]
    title = _safe_label(str(payload.get("title", "")).strip() or fallback["title"], 42)
    return {
        "title": title,
        "concept_nodes": _sanitize_labels(payload.get("concept_nodes", fallback["concept_nodes"]), 3, 20, 4, "Concept"),
        "flow_steps": _sanitize_labels(payload.get("flow_steps", fallback["flow_steps"]), 3, 24, 5, "Step"),
        "radar_axes": _sanitize_labels(payload.get("radar_axes", fallback["radar_axes"]), 3, 12, 5, "Axis"),
        "radar_scores": _sanitize_scores(payload.get("radar_scores", fallback["radar_scores"]), 5, 50, 95),
        "bar_labels": _sanitize_labels(payload.get("bar_labels", fallback["bar_labels"]), 3, 12, 4, "Part"),
        "bar_values": _sanitize_scores(payload.get("bar_values", fallback["bar_values"]), 4, 50, 95),
    }


def _youtube_search_url(topic: str) -> str:
    query = f"{topic} tutorial for beginners"
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _generate_ai_visual_image(question: str, blueprint: dict) -> str | None:
    enabled = os.getenv("OPENAI_VISUAL_IMAGE_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return None
    concept_line = ", ".join(blueprint.get("concept_nodes", [])[:4])
    flow_line = " -> ".join(blueprint.get("flow_steps", [])[:5])
    prompt = (
        "Create a clean educational infographic image for a programming learner. "
        "Use modern flat design, high contrast labels, readable typography, and minimal clutter. "
        "Do not include logos, watermarks, or dense paragraphs.\n\n"
        f"Topic: {question}\n"
        f"Title: {blueprint.get('title', '')}\n"
        f"Key concepts: {concept_line}\n"
        f"Learning flow: {flow_line}\n"
        "Visual layout: top title, middle concept map, bottom short takeaway strip."
    )
    return generate_image_data_url(prompt, size="1024x1024")


def _generate_prompt_suggestions(topic: str, style: str) -> list[str]:
    base_topic = topic.strip() or "Java exception handling"
    style = (style or "visual").strip().lower()

    style_instruction = {
        "visual": "Questions should ask for diagrams, flow maps, comparisons, and visual memory tricks.",
        "auditory": "Questions should ask for spoken explanations, recap scripts, and discussion-style understanding.",
        "kinesthetic": "Questions should ask for hands-on coding tasks, mini projects, and implementation challenges.",
    }.get(style, "Questions should match learner preference and practical understanding.")

    system_prompt = (
        "You create personalized learning prompts. Return exactly 6 lines. "
        "Each line must be one user question. No numbering, no bullets, plain text."
    )
    user_prompt = (
        f"Learning style: {style}\n"
        f"Topic: {base_topic}\n"
        f"Instruction: {style_instruction}\n"
        "Generate follow-up questions from beginner to advanced that clearly reflect the learning style."
    )
    raw = chatgpt_text(system_prompt, user_prompt, temperature=0.75)
    if raw:
        rows = [r.strip(" -\t\r") for r in raw.splitlines() if r.strip()]
        rows = [r for r in rows if len(r) > 10]
        deduped = []
        seen = set()
        for row in rows:
            key = row.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
            if len(deduped) == 6:
                break
        if len(deduped) >= 4:
            return deduped

    fallback_by_style = {
        "visual": [
            f"Can you show {base_topic} as a simple flow diagram?",
            f"What is a visual comparison chart for {base_topic}?",
            f"Give me a step-by-step visual map for {base_topic}.",
            f"Which color-coded notes should I use to remember {base_topic}?",
            f"Show one visual real-world scenario for {base_topic}.",
            f"Create a quick visual revision sheet for {base_topic}.",
        ],
        "auditory": [
            f"Explain {base_topic} like a spoken lecture for 2 minutes.",
            f"Give me a voice-style recap script for {base_topic}.",
            f"What questions should I discuss with a study partner about {base_topic}?",
            f"How can I memorize {base_topic} by speaking it aloud?",
            f"Give a conversational example for understanding {base_topic}.",
            f"Create an audio-friendly summary of {base_topic} in simple words.",
        ],
        "kinesthetic": [
            f"Give me one hands-on coding task for {base_topic}.",
            f"How can I practice {base_topic} with a mini Java project?",
            f"What implementation challenge can I solve today on {base_topic}?",
            f"Give me step-by-step task instructions for {base_topic}.",
            f"How do I test edge cases practically for {base_topic}?",
            f"Create a 20-minute coding exercise around {base_topic}.",
        ],
    }

    fallback = fallback_by_style.get(style, fallback_by_style["visual"])
    random.shuffle(fallback)
    return fallback[:6]


def _image_prompt_from_chat(
    question: str,
    style: str,
    title: str | None = None,
    summary: str | None = None,
    key_points: list[str] | None = None,
) -> str:
    base_topic = _safe_label(title or question or summary or "this topic", 90)
    style = (style or "visual").strip().lower()
    style_hint = {
        "visual": "clean infographic, clear labels, simple iconography, bright educational style",
        "auditory": "speech-bubble style visual summary, soundwave accent, minimal infographic layout",
        "kinesthetic": "step-by-step action diagram, hands-on workflow, task cards and arrows",
    }.get(style, "clean educational infographic")
    topic_points = [str(point).strip() for point in (key_points or []) if str(point).strip()]
    if not topic_points:
        topic_points = _topic_keywords(summary or question or title or base_topic)[:4]
    focus_line = ", ".join(topic_points[:4]) if topic_points else "the main concept, one example, and one key takeaway"
    return _safe_label(
        f"Create a clean educational infographic for {base_topic}. Focus on {focus_line}. Use {style_hint}. Keep labels short, add arrows or simple diagrams, and make the concept easy to study at a glance. No long paragraphs, no code blocks, no watermarks.",
        380,
    )


def _svg_data_uri(svg: str) -> str:
    return f"data:image/svg+xml;utf8,{quote(svg, safe='')}"


def _visual_bar_chart_url(blueprint: dict) -> str:
    labels = blueprint["bar_labels"]
    points = blueprint["bar_values"]
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'>"
        "<rect width='640' height='360' fill='#f7f9ff'/>"
        f"<text x='24' y='36' font-size='22' font-family='Arial' fill='#22304a'>{_safe_label(blueprint['title'], 30)} - Skill Bars</text>"
        "<line x1='60' y1='300' x2='600' y2='300' stroke='#9fb0d0' stroke-width='2'/>"
        f"<rect x='100' y='{300-int(points[0]*2)}' width='70' height='{int(points[0]*2)}' rx='8' fill='#4d6bff'/>"
        f"<rect x='220' y='{300-int(points[1]*2)}' width='70' height='{int(points[1]*2)}' rx='8' fill='#7a4dff'/>"
        f"<rect x='340' y='{300-int(points[2]*2)}' width='70' height='{int(points[2]*2)}' rx='8' fill='#9a27f0'/>"
        f"<rect x='460' y='{300-int(points[3]*2)}' width='70' height='{int(points[3]*2)}' rx='8' fill='#00a7c4'/>"
        f"<text x='96' y='325' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[0], 9)}</text>"
        f"<text x='216' y='325' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[1], 9)}</text>"
        f"<text x='336' y='325' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[2], 9)}</text>"
        f"<text x='456' y='325' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[3], 9)}</text>"
        "</svg>"
    )
    return _svg_data_uri(svg)


def _visual_mermaid_url(blueprint: dict) -> str:
    label = _safe_label(blueprint["title"], 36)
    steps = blueprint["flow_steps"]
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='760' height='240' viewBox='0 0 760 240'>"
        "<rect width='760' height='240' fill='#f7f9ff'/>"
        "<defs><marker id='arr' markerWidth='10' markerHeight='10' refX='8' refY='3' orient='auto'>"
        "<path d='M0,0 L0,6 L9,3 z' fill='#4d6bff'/></marker></defs>"
        f"<rect x='20' y='82' width='120' height='56' rx='10' fill='#e8eeff' stroke='#4d6bff'/>"
        f"<text x='32' y='116' font-size='14' font-family='Arial' fill='#22304a'>{label}</text>"
        "<rect x='170' y='82' width='120' height='56' rx='10' fill='#efe8ff' stroke='#7a4dff'/>"
        f"<text x='182' y='116' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(steps[0], 14)}</text>"
        "<rect x='320' y='82' width='140' height='56' rx='10' fill='#f4e8ff' stroke='#9a27f0'/>"
        f"<text x='330' y='116' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(steps[1], 16)}</text>"
        "<rect x='490' y='82' width='110' height='56' rx='10' fill='#e8fbff' stroke='#00a7c4'/>"
        f"<text x='500' y='116' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(steps[2], 11)}</text>"
        "<rect x='630' y='82' width='110' height='56' rx='10' fill='#e7f7ee' stroke='#2ea05f'/>"
        f"<text x='640' y='116' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(steps[3], 11)}</text>"
        "<line x1='140' y1='110' x2='170' y2='110' stroke='#4d6bff' stroke-width='2.5' marker-end='url(#arr)'/>"
        "<line x1='290' y1='110' x2='320' y2='110' stroke='#4d6bff' stroke-width='2.5' marker-end='url(#arr)'/>"
        "<line x1='460' y1='110' x2='490' y2='110' stroke='#4d6bff' stroke-width='2.5' marker-end='url(#arr)'/>"
        "<line x1='600' y1='110' x2='630' y2='110' stroke='#4d6bff' stroke-width='2.5' marker-end='url(#arr)'/>"
        "</svg>"
    )
    return _svg_data_uri(svg)


def _visual_chart_url(blueprint: dict) -> str:
    labels = blueprint["radar_axes"]
    scores = blueprint["radar_scores"]

    # five-point radar coordinates around center (320,190), radius 120
    points_xy = [
        (320, 190 - int(scores[0] * 1.2)),
        (320 + int(scores[1] * 1.12), 190 - int(scores[1] * 0.36)),
        (320 + int(scores[2] * 0.7), 190 + int(scores[2] * 0.98)),
        (320 - int(scores[3] * 0.7), 190 + int(scores[3] * 0.98)),
        (320 - int(scores[4] * 1.12), 190 - int(scores[4] * 0.36)),
    ]
    poly = " ".join(f"{x},{y}" for x, y in points_xy)

    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'>"
        "<rect width='640' height='360' fill='#f7f9ff'/>"
        f"<text x='24' y='36' font-size='22' font-family='Arial' fill='#22304a'>{_safe_label(blueprint['title'], 32)} Radar</text>"
        "<circle cx='320' cy='190' r='120' fill='none' stroke='#d8e0f5'/>"
        "<circle cx='320' cy='190' r='90' fill='none' stroke='#d8e0f5'/>"
        "<circle cx='320' cy='190' r='60' fill='none' stroke='#d8e0f5'/>"
        "<circle cx='320' cy='190' r='30' fill='none' stroke='#d8e0f5'/>"
        "<line x1='320' y1='70' x2='320' y2='310' stroke='#d8e0f5'/>"
        "<line x1='206' y1='115' x2='434' y2='265' stroke='#d8e0f5'/>"
        "<line x1='206' y1='265' x2='434' y2='115' stroke='#d8e0f5'/>"
        f"<polygon points='{poly}' fill='rgba(77,107,255,0.25)' stroke='#4d6bff' stroke-width='3'/>"
        f"<text x='290' y='60' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(labels[0], 10)}</text>"
        f"<text x='434' y='140' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(labels[1], 10)}</text>"
        f"<text x='412' y='270' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(labels[2], 10)}</text>"
        f"<text x='205' y='270' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(labels[3], 10)}</text>"
        f"<text x='175' y='145' font-size='14' font-family='Arial' fill='#22304a'>{_safe_label(labels[4], 10)}</text>"
        "</svg>"
    )
    return _svg_data_uri(svg)


def _visual_topic_image_url(blueprint: dict) -> str:
    top = _safe_label(blueprint["title"], 30)
    labels = blueprint["concept_nodes"][:3]
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'>"
        "<defs><linearGradient id='g' x1='0' x2='1' y1='0' y2='1'>"
        "<stop offset='0%' stop-color='#eef4ff'/><stop offset='100%' stop-color='#f7ebff'/></linearGradient></defs>"
        "<rect width='640' height='360' fill='url(#g)'/>"
        f"<text x='24' y='42' font-size='26' font-family='Arial' fill='#1b2a48'>{top}</text>"
        "<circle cx='120' cy='170' r='52' fill='#4d6bff22' stroke='#4d6bff' stroke-width='3'/>"
        "<circle cx='320' cy='170' r='52' fill='#7a4dff22' stroke='#7a4dff' stroke-width='3'/>"
        "<circle cx='520' cy='170' r='52' fill='#00a7c422' stroke='#00a7c4' stroke-width='3'/>"
        f"<text x='84' y='176' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[0], 10)}</text>"
        f"<text x='284' y='176' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[1], 10)}</text>"
        f"<text x='484' y='176' font-size='13' font-family='Arial' fill='#22304a'>{_safe_label(labels[2], 10)}</text>"
        "<line x1='172' y1='170' x2='268' y2='170' stroke='#4d6bff' stroke-width='2.5'/>"
        "<line x1='372' y1='170' x2='468' y2='170' stroke='#7a4dff' stroke-width='2.5'/>"
        "<text x='24' y='318' font-size='16' font-family='Arial' fill='#22304a'>AI Visual Map generated from your question</text>"
        "</svg>"
    )
    return _svg_data_uri(svg)




def _generate_ai_visual_variants(question: str, blueprint: dict) -> dict[str, str | None]:
    enabled = os.getenv("OPENAI_VISUAL_MULTI_IMAGE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return {
            "topic_image_url": None,
            "flowchart_image_url": None,
            "graph_image_url": None,
            "bar_graph_image_url": None,
        }

    title = blueprint.get("title", question)
    concepts = ", ".join(blueprint.get("concept_nodes", [])[:4])
    steps = " -> ".join(blueprint.get("flow_steps", [])[:5])
    axes = ", ".join(blueprint.get("radar_axes", [])[:5])
    bars = ", ".join(blueprint.get("bar_labels", [])[:4])

    topic_prompt = (
        "Create an educational concept-map illustration for programming students. "
        "Style: clean infographic, bright but professional, high readability, no logos. "
        f"Topic: {question}. Title: {title}. Concepts: {concepts}."
    )
    flow_prompt = (
        "Create a clear flowchart-style educational image with boxes and arrows for this programming topic. "
        "Keep text short and readable. "
        f"Topic: {question}. Process steps: {steps}."
    )
    graph_prompt = (
        "Create a radar/spider-chart style educational visual as an infographic. "
        "Show comparative dimensions with labels and values feel. "
        f"Topic: {question}. Dimensions: {axes}."
    )
    bar_prompt = (
        "Create a modern bar-chart style educational visual with labeled bars and clean axis hints. "
        f"Topic: {question}. Bar categories: {bars}."
    )

    return {
        "topic_image_url": generate_image_data_url(topic_prompt, size="1024x1024"),
        "flowchart_image_url": generate_image_data_url(flow_prompt, size="1024x1024"),
        "graph_image_url": generate_image_data_url(graph_prompt, size="1024x1024"),
        "bar_graph_image_url": generate_image_data_url(bar_prompt, size="1024x1024"),
    }
def get_quick_prompts(topic: str, style: str) -> list[str]:
    return _generate_prompt_suggestions(topic, style)


def generate_adaptive_response(question: str, style: str) -> dict:
    topic = question.strip().rstrip("?")
    ai_text = _generate_chatgpt_explanation(question, style)
    if not ai_text and not _allow_ai_fallback():
        return {"error": "OpenAI chat text unavailable", "status": 503}
    text = ai_text or _fallback_response(question, style)
    ai_used = bool(ai_text)

    if style == "visual":
        blueprint = _generate_visual_blueprint(question, text)
        ai_visual_image_url = _generate_ai_visual_image(question, blueprint)
        ai_variants = _generate_ai_visual_variants(question, blueprint)
        topic_image_url = ai_variants.get("topic_image_url") or _visual_topic_image_url(blueprint)
        flowchart_image_url = ai_variants.get("flowchart_image_url") or _visual_mermaid_url(blueprint)
        graph_image_url = ai_variants.get("graph_image_url") or _visual_chart_url(blueprint)
        bar_graph_image_url = ai_variants.get("bar_graph_image_url") or _visual_bar_chart_url(blueprint)
        used_fallback_visuals = not bool(ai_visual_image_url)
        return {
            "response_type": "visual",
            "ai_used": ai_used,
            "text": text,
            "assets": {
                "ai_image_url": ai_visual_image_url or topic_image_url,
                "diagram": " -> ".join(blueprint["flow_steps"]),
                "graph_image_url": graph_image_url,
                "bar_graph_image_url": bar_graph_image_url,
                "flowchart_image_url": flowchart_image_url,
                "topic_image_url": topic_image_url,
                "visual_gallery": [topic_image_url, flowchart_image_url, graph_image_url, bar_graph_image_url],
                "video_url": _youtube_search_url(topic),
                "gif_url": "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif",
                "suggested_downloads": ["video"],
                "visual_status": "fallback_generated" if used_fallback_visuals else "ai_image_generated",
            },
        }

    if style == "auditory":
        return {
            "response_type": "auditory",
            "ai_used": ai_used,
            "text": text,
            "assets": {
                "audio_script": f"Audio-style explanation for {topic}. {text}",
                "suggested_downloads": ["audio"],
            },
        }

    starter_code = (
        "public class ExceptionDemo {\n"
        "  public static void main(String[] args) {\n"
        "    try {\n"
        "      int[] values = {1, 2, 3};\n"
        "      int result = values[4];\n"
        "      System.out.println(result);\n"
        "    } catch (ArrayIndexOutOfBoundsException e) {\n"
        "      System.out.println(\"Handled: \" + e.getMessage());\n"
        "    } finally {\n"
        "      System.out.println(\"Cleanup complete\");\n"
        "    }\n"
        "  }\n"
        "}"
    )
    return {
        "response_type": "kinesthetic",
        "ai_used": ai_used,
        "text": text,
        "assets": {
            "starter_code": starter_code,
            "task_sheet": "Implement try-catch-finally and test two failure cases.",
            "suggested_downloads": ["task_sheet", "solution"],
        },
    }


CHAT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "answer": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "example": {"type": "string"},
        "code_sample": {"type": "string"},
        "practice": {"type": "string"},
        "quiz_question": {"type": "string"},
        "quiz_options": {"type": "array", "items": {"type": "string"}},
        "follow_up_prompts": {"type": "array", "items": {"type": "string"}},
        "next_step": {"type": "string"},
        "image_prompt": {"type": "string"},
        "confidence": {"type": "string"},
        "mode": {"type": "string"},
        "style": {"type": "string"},
    },
    "required": [
        "title",
        "summary",
        "answer",
        "key_points",
        "example",
        "code_sample",
        "practice",
        "quiz_question",
        "quiz_options",
        "follow_up_prompts",
        "next_step",
        "image_prompt",
        "confidence",
        "mode",
        "style",
    ],
    "additionalProperties": False,
}


def _history_text(recent_history: list[dict] | None) -> str:
    rows = recent_history or []
    lines = []
    for item in rows[-8:]:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content[:500]}")
    return "\n".join(lines)


def _key_points_from_text(text: str, limit: int = 5) -> list[str]:
    sentences = [segment.strip(" -•\t") for segment in re.split(r"[\n.!?]+", text or "") if segment.strip()]
    points: list[str] = []
    seen = set()
    for sentence in sentences:
        clean = _safe_label(sentence, 110)
        if len(clean) < 12:
            continue
        lowered = clean.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        points.append(clean)
        if len(points) == limit:
            break
    return points


def _code_sample_for_topic(question: str, style: str, base_assets: dict | None = None) -> str:
    assets = base_assets or {}
    starter = str(assets.get("starter_code") or "").strip()
    if starter:
        return starter

    topic = question.strip().rstrip("?") or "the topic"
    lower = topic.lower()
    if "python" in lower or style == "visual":
        return (
            "def solve():\n"
            "    value = int(input().strip())\n"
            "    print('Even' if value % 2 == 0 else 'Odd')\n\n"
            "solve()"
        )
    if "java" in lower:
        return (
            "import java.util.Scanner;\n\n"
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    Scanner sc = new Scanner(System.in);\n"
            "    int value = sc.nextInt();\n"
            "    System.out.println(value % 2 == 0 ? \"Even\" : \"Odd\");\n"
            "  }\n"
            "}"
        )
    if "javascript" in lower or "js" in lower:
        return (
            "const fs = require('fs');\n"
            "const value = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "console.log(value % 2 === 0 ? 'Even' : 'Odd');"
        )
    if "c++" in lower or "cpp" in lower:
        return (
            "#include <iostream>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    int value;\n"
            "    cin >> value;\n"
            "    cout << (value % 2 == 0 ? \"Even\" : \"Odd\");\n"
            "    return 0;\n"
            "}"
        )
    if lower == "c" or re.search(r"\bc\b", lower):
        return (
            "#include <stdio.h>\n\n"
            "int main() {\n"
            "    int value;\n"
            "    scanf(\"%d\", &value);\n"
            "    printf(value % 2 == 0 ? \"Even\" : \"Odd\");\n"
            "    return 0;\n"
            "}"
        )
    return ""


def _fallback_chat_response(question: str, style: str, mode: str, recent_history: list[dict] | None = None) -> dict:
    base = _fallback_response(question, style)
    title = _safe_label(question or "Conversation", 40)
    key_points = [line.strip("- ").strip() for line in base.splitlines() if line.strip()][:5]
    if not key_points:
        key_points = ["Clarify the goal", "Break the problem into steps", "Test with edge cases"]
    code_sample = _code_sample_for_topic(question, style)
    image_prompt = _image_prompt_from_chat(question, style, title=title, summary=base, key_points=key_points)
    return {
        "title": title,
        "summary": f"A {mode} response for {question.strip() or 'your topic'} with a clear breakdown.",
        "answer": base,
        "key_points": key_points[:5],
        "example": f"For {question.strip() or 'this topic'}, apply the idea to a small real-world workflow.",
        "code_sample": code_sample,
        "practice": f"Write one tiny exercise for {question.strip() or 'this topic'} and solve it from scratch.",
        "quiz_question": f"What is the main idea behind {question.strip() or 'this topic'}?",
        "quiz_options": ["Identify the concept", "Ignore edge cases", "Skip testing", "Jump to the final answer"],
        "follow_up_prompts": _generate_prompt_suggestions(question, style)[:4],
        "next_step": "Try one quick example, then test an edge case.",
        "image_prompt": image_prompt,
        "confidence": "High",
        "mode": mode,
        "style": style,
    }


def _allow_ai_fallback() -> bool:
    return os.getenv("ALLOW_AI_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


def generate_chat_response(
    question: str,
    style: str,
    mode: str,
    recent_history: list[dict] | None = None,
) -> dict:
    chatbot_config = get_chatbot_config()
    if not chatbot_config.enabled:
        return {"error": "Chatbot is temporarily disabled by admin", "status": 503}

    mode_key = (mode or "detailed").strip().lower()
    if mode_key not in {"concise", "detailed", "eli5", "exam"}:
        mode_key = "detailed"

    style_key = (style or "visual").strip().lower()
    if style_key not in {"visual", "auditory", "kinesthetic"}:
        style_key = "visual"

    base = generate_adaptive_response(question, style_key)
    if isinstance(base, dict) and base.get("error"):
        return base
    history_text = _history_text(recent_history)
    base_text = str(base.get("text", "") or "").strip()
    base_assets = base.get("assets", {}) if isinstance(base.get("assets", {}), dict) else {}

    admin_prompt = str(chatbot_config.system_prompt or DEFAULT_CHATBOT_PROMPT).strip()
    system_prompt = (
        f"{admin_prompt}\n"
        f"Assistant name: {chatbot_config.assistant_name}.\n"
        f"Admin response style: {chatbot_config.response_style}.\n"
        "Return polished JSON only, with a natural conversational answer plus organized support fields. "
        "The answer must sound human and direct, not robotic. "
        "Use concise, useful section values that make the UI easy to read."
    )
    user_prompt = (
        f"User question: {question}\n"
        f"Learning style hint: {style_key}\n"
        f"Response tone: {mode_key}\n\n"
        f"Recent conversation:\n{history_text or 'No prior context.'}\n\n"
        f"Reference content from the tutor engine:\n{base_text[:2400]}\n\n"
        "Create a polished response payload with these expectations:\n"
        "- title: short descriptive title\n"
        "- summary: one-sentence overview\n"
        "- answer: natural, clear main answer\n"
        "- key_points: 3 to 5 crisp takeaways\n"
        "- example: a concrete example or analogy\n"
        "- code_sample: a short code snippet only if the topic benefits from code, otherwise empty string\n"
        "- practice: one small practice prompt\n"
        "- quiz_question: one quick check question\n"
        "- quiz_options: 3 to 4 answer choices\n"
        "- follow_up_prompts: 3 to 4 helpful next questions\n"
        "- next_step: a practical next action\n"
        "- confidence: High, Medium, or Low\n"
        "- mode: use the requested response tone\n"
        "- style: use the learning style hint\n"
    )

    structured = openai_json_schema(system_prompt, user_prompt, CHAT_RESPONSE_SCHEMA, "chat_response", temperature=0.35)
    if not structured:
        if not _allow_ai_fallback():
            return {"error": "OpenAI chat response unavailable", "status": 503}
        structured = _fallback_chat_response(question, style_key, mode_key, recent_history)

    answer = str(structured.get("answer") or base_text or _fallback_response(question, style_key)).strip()
    summary = str(structured.get("summary") or answer[:180]).strip()
    key_points = structured.get("key_points") or _key_points_from_text(answer, limit=5)
    if not key_points:
        key_points = ["Clarify the goal", "Break the problem into steps", "Test the edge cases"]
    example = str(structured.get("example") or "").strip()
    code_sample = str(structured.get("code_sample") or "").strip() or _code_sample_for_topic(question, style_key, base_assets)
    practice = str(structured.get("practice") or "").strip()
    quiz_question = str(structured.get("quiz_question") or "").strip()
    quiz_options = structured.get("quiz_options") or []
    if not isinstance(quiz_options, list):
        quiz_options = []
    follow_up_prompts = structured.get("follow_up_prompts") or []
    if not isinstance(follow_up_prompts, list):
        follow_up_prompts = []
    follow_up_prompts_clean = [str(item).strip() for item in follow_up_prompts[:4] if str(item).strip()]
    next_step = str(structured.get("next_step") or "").strip()
    image_prompt = str(structured.get("image_prompt") or "").strip()
    if not image_prompt:
        image_prompt = _image_prompt_from_chat(
            question,
            style_key,
            title=str(structured.get("title") or "").strip(),
            summary=str(structured.get("summary") or "").strip() or answer,
            key_points=[str(item).strip() for item in (structured.get("key_points") or []) if str(item).strip()],
        )
    confidence = str(structured.get("confidence") or "High").strip().title()
    if confidence not in {"High", "Medium", "Low"}:
        confidence = "High"

    max_chars = int(chatbot_config.max_response_chars or 1200)
    if max_chars > 0:
        answer = answer[:max_chars]
        summary = summary[: max(120, min(max_chars, 260))]

    return {
        "title": str(structured.get("title") or _safe_label(question or "Conversation", 40)).strip(),
        "summary": summary,
        "answer": answer,
        "text": answer,
        "key_points": [str(item).strip() for item in key_points[:5] if str(item).strip()],
        "example": example,
        "code_sample": code_sample,
        "practice": practice,
        "quiz_question": quiz_question,
        "quiz_options": [str(item).strip() for item in quiz_options[:4] if str(item).strip()],
        "next_step": next_step,
        "image_prompt": image_prompt,
        "confidence": confidence,
        "response_type": base.get("response_type", style_key),
        "ai_used": bool(base.get("ai_used")),
        "assets": {
            **base_assets,
            "quiz_options": [str(item).strip() for item in quiz_options[:4] if str(item).strip()],
        },
        "follow_up_prompts": follow_up_prompts_clean or _generate_prompt_suggestions(question, style_key)[:4],
        "mode": mode_key,
        "style": style_key,
    }
