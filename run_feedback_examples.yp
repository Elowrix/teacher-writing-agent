from feedback_agent import generate_feedback

def run_feedback_examples():
    prompt = "Why is your university a good place to study?"
    student_paragraph = (
        "My university is a good place to study. "
        "First, the teachers are helpful. "
        "Second, the school has a big library. "
        "Students can also join clubs."
    )

    feedback = generate_feedback(prompt, student_paragraph)

    print("Prompt:", prompt)
    print("Student paragraph:", student_paragraph)

    print("\nStrengths:")
    for item in feedback["strengths"]:
        print("-", item)

    print("\nProblems:")
    for item in feedback["problems"]:
        print("-", item)

    print("\nSuggestions:")
    for item in feedback["suggestions"]:
        print("-", item)

if __name__ == "__main__":
    run_feedback_examples()
