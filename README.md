# Weby

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | API key for OpenAI-compatible service |
| `OPENAI_API_BASE` | ❌ | `https://openrouter.ai/api/v1` | Base URL for OpenAI-compatible API |
| `WEBY_URL` | ❌ | `http://127.0.0.1:9999` | Weby service URL (Required only for test client) |
| `RATE_LIMIT` | ❌ | `256` | Rate limit per minute per IP |
| `ALLOWED_ORIGINS` | ❌ | `*` | CORS allowed origins (comma-separated) |
| `API_KEYS` | ❌ | `""` | Valid API keys for authentication (comma-separated) |
| `TIMEOUT` | ❌ | `1200` | Request timeout in seconds |
| `DEBUG` | ❌ | `False` | Enable debug mode |
| `MODEL` | ❌ | `deepseek/deepseek-r1-0528` | Default AI model for code generation |

## Example .env

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://openrouter.ai/api/v1
MODEL=deepseek/deepseek-r1-0528
API_KEYS=key1,key2,key3
RATE_LIMIT=100
ALLOWED_ORIGINS=https://yourapp.com,http://localhost:3000
TIMEOUT=600
DEBUG=False
```

## /studio Endpoint
The /studio endpoint provides a structured, stepwise execution flow powered by large language models. It generates a high-level plan and then executes each step in sequence, streaming the results using Server-Sent Events (SSE).

### Request
**POST** /v2/studio?stream=true

**Body** (OpenAI-compatible schema):


```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Describe the task you want help with..."
    }
  ],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 512,
  "stream": true
}
```
 
### Plan structure
The initial message in the stream includes a full plan with high-level context.


```json
{
  "content": {
    "type": "plan",
    "task_title": "Create example and test files in project structure",
    "task_description": "The goal is to create a Python script named `example.py` in the `src` directory and a corresponding test file...",
    "steps": [
      "Clarify task requirements",
      "Create example.py",
      "Create test_example.py"
    ]
  },
  "tool_calls": null
}
```

### Step Execution Output
Each step in the plan streams results incrementally as a JSON object, which may include **textual content**, **tool calls**, or **both**. 
These are wrapped as Server-Sent Events (SSE) in the response stream.

Example output:
```json
{
  "content": "Here is the implementation for the first function...",
  "tool_calls": [
    {
      "name": "write_file",
      "arguments": "{ \"path\": \"src/example.py\", \"content\": \"...\" }"
    }
  ]
}
```

- ```content```: Textual output generated for the step (e.g., explanations, code, summaries).

- ```tool_calls```: Tool function invocations (e.g., ```write_file```, ```read_file```, etc.) with structured arguments.

This design allows your client to display partial results in real-time and perform tool-side actions as needed during execution.

## Supported Tools

The Studio agent may call structured tools to perform file operations, code edits, or system-level tasks. Below are the currently available tools:

| Name | Description | Required Parameters |
|------|-------------|---------------------|
| `codebase_search` | Find relevant code snippets across your codebase using semantic search. | `query` |
| `edit_file` | Apply changes to an existing file. | `path`, `edits` |
| `find` | Search for files or directories using glob patterns. | `pattern` |
| `grep_search` | Search for a pattern within files. | `pattern`, `path` |
| `list_directory` | List the contents of a directory with details like file sizes and child count. | `directory` |
| `run_command` | Execute a shell command with arguments. | `command` |
| `view_code_item` | Display a function or class definition from a given path. | `item_name`, `path` |
| `view_file` | View the contents of a specific file. | `path` |
| `write_file` | Create or overwrite a file with given content. | `path`, `content` |

### Example Tool Call

```json
{
  "name": "write_file",
  "arguments": "{ \"path\": \"main.py\", \"content\": \"print('Hello')\" }"
}
```

Each tool call is streamed during execution and may be automatically handled by the client or used for audit/logging purposes.
