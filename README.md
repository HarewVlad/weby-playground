# Weby

## Install
```
pip install -r requirements.txt
```

## Run
```
python main.py
```

## Website

### Install
```
npx shadcn@latest init (Call it "website")
npx shadcn@latest add button
...
cd website
```

### Run
```
npm run dev
```


### Take screenshot

```bash
# Custom format and quality
curl -X POST http://localhost:3000/screenshot \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:3000",
    "format": "jpeg",
    "quality": 95,
    "width": 1920,
    "height": 1080
  }' > screenshot.jpg

# Screenshot of external URL
curl -X POST http://localhost:3000/screenshot \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "full_page": false
  }' > external-screenshot.png
```

## Server

### Example non-stream request
```bash
curl -X POST "http://localhost:9999/v1/weby" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "messages": [
      {
        "role": "user", 
        "content": "Hi, how are you?"
      }
    ],
    "stream": false,
    "framework": "Nextjs",
    "temperature": 0.7,
    "top_p": 0.95,
    "model": "anthropic/claude-3.5-sonnet"
  }'
```