import uuid
from src.workflow import Workflow

def main():
    # Initialize workflow
    wf = Workflow()

    conversation_id = str(uuid.uuid4())  # Generate a unique conversation ID
    
    user_query = "How long is the engineering program at EMINES?"

    print("\n=== Testing Workflow ===")
    print("User Query:", user_query)
    print("Conversation ID:", conversation_id)

    # Run workflow
    history = wf.run_text(user_query, conversation_id=conversation_id)

    print("\n=== Chat History ===")

    for message in history:
        role = message["role"].capitalize()
        content = message["content"]
        print(f"{role}: {content}\n")

    print("=== Test Completed ===")


if __name__ == "__main__":
    main()