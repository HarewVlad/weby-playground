import os
from smolagents import CodeAgent, OpenAIServerModel, ToolCollection, LiteLLMModel
from mcp import StdioServerParameters

from config import Config
from utils import get_project_structure


base_model = OpenAIServerModel(
    model_id="google/gemma-3-27b-it",
    api_base="https://openrouter.ai/api/v1",
    api_key=Config.OPENROUTER_API_KEY,
)

project_path = os.path.join(os.getcwd(), "website")

filesystem_server_parameters = StdioServerParameters(
    command="npx",
    args=[
        "-y",
        "@modelcontextprotocol/server-filesystem",
        project_path,
    ],
)


def chat_loop():
    print("Welcome to the Agent Chat! Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    with ToolCollection.from_mcp(
        filesystem_server_parameters, trust_remote_code=True
    ) as tool_collection:
        agent = CodeAgent(
            model=base_model,
            tools=[*tool_collection.tools],
            max_steps=15,
            # planning_interval=5,
            additional_authorized_imports=["open", "os"],
        )

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
                        formatted_input += (
                            f"{msg['role'].capitalize()}: {msg['content']}\n"
                        )
                else:
                    formatted_input = user_input

                response = agent.run(
                    user_input,
                    additional_args=dict(
                        project_path="/root/web-creator/website",
                        project_info="This web project uses Node.js + TailwindCSS.",
                        project_structure=get_project_structure(
                            project_path, ["node_modules", "style.css"]
                        ),
                    ),
                )
                print("Weby:", response)

                chat_history.append({"role": "assistant", "content": response})
            except Exception as e:
                print(f"\nError: {str(e)}")

            print("-" * 50)


if __name__ == "__main__":
    chat_loop()
