def detect_task_type(prompt):
    prompt = prompt.lower()

    if "why" in prompt:
        return "why"
    elif "how" in prompt:
        return "how"
    elif "problem" in prompt:
        return "problem-focused"
    else:
        return "descriptive"


def generate_topic_sentence(task_type, prompt):
    if task_type == "how":
        return "Students can improve their English in three effective ways."
    elif task_type == "why":
        return "My university is an ideal place to study for three main reasons."
    elif task_type == "problem-focused":
        return "Cities have many serious problems for three important reasons."
    else:
        return "My ideal city is a great place to live for three main reasons."


def generate_supporting_ideas(task_type, prompt, count=3):
    if task_type == "how":
        return [
            "students can practice reading and writing every day",
            "they can listen to English podcasts and videos",
            "they can speak regularly with others"
        ]
    elif task_type == "why":
        return [
            "the teachers are supportive and experienced",
            "the university has modern facilities",
            "there are many social activities"
        ]
    elif task_type == "problem-focused":
        return [
            "traffic causes delays and stress",
            "pollution affects people's health",
            "housing is expensive"
        ]
    else:
        return [
            "it is clean and safe",
            "it has good public transport",
            "it offers many opportunities"
        ]


def build_paragraph(topic_sentence, ideas, task_type):
    paragraph = topic_sentence + " "

    paragraph += f"First, {ideas[0]}. "
    paragraph += f"Second, {ideas[1]}. "
    paragraph += f"Third, {ideas[2]}. "

    paragraph += "In conclusion, these points make it a very good choice."

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
