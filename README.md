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