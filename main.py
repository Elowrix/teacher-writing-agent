from writing_agent import (
    detect_task_type,
    generate_topic_sentence,
    generate_supporting_ideas,
    build_paragraph,
    consistency_check
)

def main():
    print("Teacher Writing Agent")
    print("-" * 22)

    prompt = input("Please enter a paragraph writing prompt: ")

    task_type = detect_task_type(prompt)
    topic_sentence = generate_topic_sentence(task_type, prompt)
    ideas = generate_supporting_ideas(task_type, prompt)
    paragraph = build_paragraph(topic_sentence, ideas, task_type)
    result = consistency_check(paragraph, task_type)

    print("\nDetected task type:", task_type)
    print("\nGenerated paragraph:")
    print(paragraph)
    print("\nConsistency check result:", result)

if __name__ == "__main__":
    main()
