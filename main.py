import sys
from writing_agent import (
    detect_task_type,
    generate_topic_sentence,
    generate_supporting_ideas,
    build_paragraph,
    consistency_check
)
from feedback_agent import generate_feedback


def run_prompt(prompt):
    task_type = detect_task_type(prompt)
    topic_sentence = generate_topic_sentence(task_type, prompt)
    ideas = generate_supporting_ideas(task_type, prompt)
    paragraph = build_paragraph(topic_sentence, ideas, task_type)
    result = consistency_check(paragraph, task_type)

    print("\nDetected task type:", task_type)
    print("\nGenerated paragraph:")
    print(paragraph)
    print("\nConsistency check result:", result)


def run_feedback_mode():
    prompt = input("Enter the original paragraph prompt: ")
    paragraph = input("Paste the student's paragraph: ")

    feedback = generate_feedback(prompt, paragraph)

    print("\nFeedback")
    print("-" * 8)

    print("\nStrengths:")
    if feedback["strengths"]:
        for item in feedback["strengths"]:
            print("-", item)
    else:
        print("- No clear strengths were identified.")

    print("\nProblems:")
    if feedback["problems"]:
        for item in feedback["problems"]:
            print("-", item)
    else:
        print("- No major problems were identified.")

    print("\nSuggestions:")
    if feedback["suggestions"]:
        for item in feedback["suggestions"]:
            print("-", item)
    else:
        print("- Keep developing your ideas with clearer details.")


def main():
    print("Teacher Writing Agent")
    print("-" * 22)
    print("1. Generate a sample paragraph")
    print("2. Get feedback on a student paragraph")

    choice = input("Choose an option (1 or 2): ")

    if choice == "1":
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
            run_prompt(prompt)
            return

        try:
            prompt = input("Please enter a paragraph writing prompt: ")
        except EOFError:
            print("\nNo interactive input was provided.")
            return

        run_prompt(prompt)

    elif choice == "2":
        try:
            run_feedback_mode()
        except EOFError:
            print("\nNo interactive input was provided.")
            return

    else:
        print("Invalid choice. Please run the program again and choose 1 or 2.")


if __name__ == "__main__":
    main()
