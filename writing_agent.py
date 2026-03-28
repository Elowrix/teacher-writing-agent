import re


def detect_task_type(prompt):
    prompt_lower = prompt.lower()

    if "why" in prompt_lower:
        return "why"
    elif "how" in prompt_lower:
        return "how"
    elif "problem" in prompt_lower or "problems" in prompt_lower:
        return "problem-focused"
    else:
        return "descriptive"


def extract_topic(prompt, task_type):
    prompt = prompt.strip()

    if task_type == "how":
        topic = re.sub(r"(?i)^how can\s+", "", prompt)
        topic = topic.rstrip("?.! ")
        return topic if topic else "people improve their lives"

    elif task_type == "why":
        topic = re.sub(r"(?i)^why is\s+", "", prompt)
        topic = re.sub(r"(?i)^why are\s+", "", topic)
        topic = topic.rstrip("?.! ")
        return topic if topic else "this topic important"

    elif task_type == "problem-focused":
        topic = prompt.lower().replace("write a paragraph about", "").strip()
        topic = topic.rstrip("?.! ")
        return topic if topic else "cities"

    else:
        topic = re.sub(r"(?i)^write a paragraph about\s+", "", prompt)
        topic = topic.rstrip("?.! ")
        return topic if topic else "this topic"


def generate_topic_sentence(task_type, prompt):
    topic = extract_topic(prompt, task_type)

    if task_type == "how":
        return f"{topic.capitalize()} in three effective ways."
    elif task_type == "why":
        return f"{topic.capitalize()} for three main reasons."
    elif task_type == "problem-focused":
        return f"{topic.capitalize()} have several important problems."
    else:
        return f"{topic.capitalize()} is important for three main reasons."


def generate_supporting_ideas(task_type, prompt, count=3):
    topic = extract_topic(prompt, task_type).lower()

    if "happy" in topic or "happiness" in topic:
        return [
            "they can spend time with family and friends",
            "they can live a healthy and balanced life",
            "they can do activities they enjoy"
        ]
    elif "english" in topic:
        return [
            "people can practice reading and writing regularly",
            "they can listen to English podcasts and videos",
            "they can speak English with others as often as possible"
        ]
    elif "university" in topic:
        return [
            "it offers a good academic environment",
            "it has useful facilities and resources",
            "it provides social and personal development opportunities"
        ]
    elif "city" in topic and task_type == "problem-focused":
        return [
            "traffic causes stress and delays",
            "pollution affects people's health",
            "housing can be too expensive"
        ]
    elif "city" in topic:
        return [
            "it can offer many job and education opportunities",
            "it can provide good public services",
            "it can make daily life more convenient"
        ]
    elif task_type == "how":
        return [
            "people can develop useful daily habits",
            "they can learn from others and new experiences",
            "they can stay consistent and motivated"
        ]
    elif task_type == "why":
        return [
            "it has many positive features",
            "it supports people in different ways",
            "it creates valuable opportunities"
        ]
    elif task_type == "problem-focused":
        return [
            "it creates difficulties in daily life",
            "it affects people's well-being",
            "it causes long-term social challenges"
        ]
    else:
        return [
            "it has several positive aspects",
            "it can improve people's lives in different ways",
            "it offers useful opportunities and benefits"
        ]


def build_paragraph(topic_sentence, ideas, task_type):
    if task_type == "problem-focused":
        conclusion = "In conclusion, these problems show that this issue needs serious attention."
    elif task_type == "how":
        conclusion = "In conclusion, these steps can help people achieve better results."
    elif task_type == "why":
        conclusion = "In conclusion, these reasons make it clear why this topic is important."
    else:
        conclusion = "In conclusion, these points show why this topic is important."

    paragraph = topic_sentence + " "
    paragraph += f"First, {ideas[0]}. "
    paragraph += f"Second, {ideas[1]}. "
    paragraph += f"Third, {ideas[2]}. "
    paragraph += conclusion

    return paragraph


def consistency_check(paragraph, task_type):
    checks = []

    if "First" in paragraph and "Second" in paragraph and "Third" in paragraph:
        checks.append("structure ok")
    else:
        checks.append("missing structure")

    if "In conclusion" in paragraph:
        checks.append("conclusion ok")
    else:
        checks.append("missing conclusion")

    return "PASS" if "missing" not in " ".join(checks) else "FAIL"
