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

## Test CURL requests

```bash
# Test 1: CSV File Upload
curl -X POST http://localhost:8000/v1/weby \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Analyze this sales data and tell me which product performed best"
      }
    ],
    "model": "deepseek/deepseek-r1-0528",
    "temperature": 0.7,
    "top_p": 1.0,
    "framework": "Nextjs",
    "uploaded_files": [
      {
        "filename": "sales_data.csv",
        "content": "product_name,category,quantity_sold,revenue,profit_margin,date\nLaptop Pro X1,Electronics,145,217500.00,0.25,2024-01-15\nSmartphone Z10,Electronics,523,261500.00,0.30,2024-01-15\nWireless Earbuds,Accessories,892,89200.00,0.45,2024-01-15\nTablet Ultra,Electronics,67,33500.00,0.22,2024-01-15\nUSB-C Hub,Accessories,234,7020.00,0.55,2024-01-15\nGaming Mouse,Peripherals,156,12480.00,0.40,2024-01-15\nMechanical Keyboard,Peripherals,89,8900.00,0.35,2024-01-15\n4K Webcam,Electronics,45,6750.00,0.28,2024-01-15"
      }
    ]
  }'
```

```bash
# Test 2: XML File Upload
curl -X POST http://localhost:8000/v1/weby \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Parse this configuration and tell me what database settings are configured"
      }
    ],
    "model": "deepseek/deepseek-r1-0528",
    "temperature": 0.7,
    "top_p": 1.0,
    "framework": "Nextjs",
    "project_files": [
      {
        "filename": "config/app_settings.xml",
        "content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<configuration>\n  <application name=\"MyApp\" version=\"2.1.0\">\n    <settings>\n      <debug enabled=\"true\"/>\n      <logging level=\"INFO\" maxFileSize=\"10MB\"/>\n    </settings>\n  </application>\n  <database>\n    <primary>\n      <host>db-primary.example.com</host>\n      <port>5432</port>\n      <name>production_db</name>\n      <pool minConnections=\"5\" maxConnections=\"20\"/>\n      <ssl enabled=\"true\" mode=\"require\"/>\n    </primary>\n    <replica>\n      <host>db-replica.example.com</host>\n      <port>5432</port>\n      <name>production_db</name>\n      <pool minConnections=\"2\" maxConnections=\"10\"/>\n    </replica>\n  </database>\n  <cache>\n    <redis host=\"cache.example.com\" port=\"6379\">\n      <ttl default=\"3600\" max=\"86400\"/>\n    </redis>\n  </cache>\n</configuration>"
      }
    ]
  }'
```

```bash
# Test 3: Combined CSV and XML in one request
curl -X POST http://localhost:8000/v1/weby \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "I have sales data and system configuration. Can you check if our database can handle the transaction volume based on the sales?"
      }
    ],
    "model": "deepseek/deepseek-r1-0528",
    "temperature": 0.7,
    "top_p": 1.0,
    "framework": "Nextjs",
    "uploaded_files": [
      {
        "filename": "daily_transactions.csv",
        "content": "timestamp,transaction_id,amount,status\n2024-01-15 08:00:00,TXN001,150.00,completed\n2024-01-15 08:01:00,TXN002,89.99,completed\n2024-01-15 08:02:00,TXN003,1200.00,pending\n2024-01-15 08:03:00,TXN004,45.50,completed\n2024-01-15 08:04:00,TXN005,799.00,failed"
      }
    ],
    "project_files": [
      {
        "filename": "config/database.xml",
        "content": "<?xml version=\"1.0\"?>\n<database_config>\n  <connection_pool max=\"50\" timeout=\"30\"/>\n  <performance>\n    <max_transactions_per_second>1000</max_transactions_per_second>\n    <query_timeout>5</query_timeout>\n  </performance>\n</database_config>"
      }
    ]
  }'
```

```bash
curl -X POST "http://localhost:8000/v1/weby" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "framework": "Nextjs",
    "messages": [
      {
        "role": "user",
        "content": "Create a landing page based on this wireframe image"
      }
    ],
    "uploaded_files": [
      {
        "filename": "wireframe.png",
        "content": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
      }
    ],
    "temperature": 0.7,
    "top_p": 0.9
  }'
```