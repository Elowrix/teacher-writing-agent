def analyze_structure(paragraph):
    feedback = []

    if len(paragraph.split()) < 30:
        feedback.append("The paragraph is too short. Add more supporting details.")

    if "first" in paragraph.lower():
        feedback.append("The paragraph includes a first supporting idea.")
    else:
        feedback.append("The paragraph does not clearly introduce the first supporting idea with a transition word like 'First'.")

    if "second" in paragraph.lower():
        feedback.append("The paragraph includes a second supporting idea.")
    else:
        feedback.append("The paragraph does not clearly introduce the second supporting idea with a transition word like 'Second'.")

    if "third" in paragraph.lower():
        feedback.append("The paragraph includes a third supporting idea.")
    else:
        feedback.append("The paragraph does not clearly introduce the third supporting idea with a transition word like 'Third'.")

    if "in conclusion" in paragraph.lower():
        feedback.append("The paragraph includes a concluding sentence.")
    else:
        feedback.append("The paragraph does not include a clear concluding sentence.")

    return feedback


def check_topic_relevance(paragraph, prompt):
    prompt_words = set(prompt.lower().replace("?", "").replace(".", "").split())
    paragraph_words = set(paragraph.lower().replace("?", "").replace(".", "").split())

    common_words = prompt_words.intersection(paragraph_words)

    if len(common_words) >= 2:
        return "The paragraph seems relevant to the prompt."
    else:
        return "The paragraph may not be fully relevant to the prompt. Make sure you address the topic clearly."


def generate_feedback(prompt, paragraph):
    structure_feedback = analyze_structure(paragraph)
    relevance_feedback = check_topic_relevance(paragraph, prompt)

    strengths = []
    problems = []
    suggestions = []

    for item in structure_feedback:
        if "includes" in item:
            strengths.append(item)
        else:
            problems.append(item)

    if "seems relevant" in relevance_feedback:
        strengths.append(relevance_feedback)
    else:
        problems.append(relevance_feedback)

    if any("too short" in item for item in structure_feedback):
        suggestions.append("Add more supporting details and examples.")
    if not any("concluding sentence" in item and "includes" in item for item in structure_feedback):
        suggestions.append("Add a concluding sentence beginning with 'In conclusion'.")
    if not any("first supporting idea" in item and "includes" in item for item in structure_feedback):
        suggestions.append("Use transition words such as 'First', 'Second', and 'Third' to organize your ideas.")
    if "may not be fully relevant" in relevance_feedback:
        suggestions.append("Make sure your ideas directly answer the prompt.")

    return {
        "strengths": strengths,
        "problems": problems,
        "suggestions": suggestions
    }
