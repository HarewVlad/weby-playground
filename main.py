from smolagents import CodeAgent, LiteLLMModel, AgentImage, OpenAIServerModel
from dotenv import load_dotenv
import os

from filesystem_tools import filesystem_tools
from descriptions import (
    full_stack_software_engineer_agent_description,
)

# Load environment variables
load_dotenv()

base_model_params = {
    "temperature": 1.0,
    "top_k": 64,
    "top_p": 0.95,
    "max_tokens": 8192,
}

base_model = OpenAIServerModel(
    model_id="google/gemma-3-27b-it",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

agent = CodeAgent(
    model=base_model,
    tools=filesystem_tools,
    max_steps=15,
    planning_interval=5,
    additional_authorized_imports=["open", "os"],
)


def chat_loop():
    print("Welcome to the Agent Chat! Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    chat_history = []

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() in ["exit", "quit"]:
            print("\nExiting chat. Goodbye!")
            break

        chat_history.append({"role": "user", "content": user_input})

        try:
            if len(chat_history) > 1:
                formatted_input = f"User input: {user_input}\n\nChat history:\n"
                max_history = min(16, len(chat_history) - 1)
                for i in range(
                    len(chat_history) - max_history - 1, len(chat_history) - 1
                ):
                    msg = chat_history[i]
                    formatted_input += f"{msg['role'].capitalize()}: {msg['content']}\n"
            else:
                formatted_input = user_input

            response = agent.run(
                user_input,
                additional_args=dict(
                    project_path="/root/web-creator/website",
                    bias="Always preserve original style of the website when adding new elements or changing something.",
                ),
            )
            print("\nOrchestrator:", response)

            chat_history.append({"role": "assistant", "content": response})
        except Exception as e:
            print(f"\nError: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
