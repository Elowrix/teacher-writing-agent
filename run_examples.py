from writing_agent import (
    detect_task_type,
    generate_topic_sentence,
    generate_supporting_ideas,
    build_paragraph,
    consistency_check
)

def run_examples():
    examples = [
        "Write a paragraph about your ideal city.",
        "Write a paragraph about the problems of a city.",
        "Why is your university a good place to study?",
        "How can students improve their English?"
    ]

    for prompt in examples:
        task_type = detect_task_type(prompt)
        topic_sentence = generate_topic_sentence(task_type, prompt)
        ideas = generate_supporting_ideas(task_type, prompt)
        paragraph = build_paragraph(topic_sentence, ideas, task_type)
        result = consistency_check(paragraph, task_type)

        print(f"Prompt: {prompt}")
        print(f"Detected task type: {task_type}")
        print(f"Generated paragraph: {paragraph}")
        print(f"Consistency check result: {result}")
        print("-" * 50)

if __name__ == "__main__":
    run_examples()
