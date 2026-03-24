## Model Selection

| Model | ID | Best For |
|-------|-----|----------|
| Opus 4.6 | `claude-opus-4-6` | Complex reasoning, architecture, research |
| Sonnet 4.6 | `claude-sonnet-4-6` | Balanced coding, most development tasks |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | Fast responses, high-volume, cost-sensitive |

Default to Sonnet 4.6 unless the task requires deep reasoning (Opus) or speed/cost optimization (Haiku).

## Python SDK

**Installation:**

```bash
pip install anthropic
```

**Basic message:**

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Explain async/await in Python"}
    ]
)
print(message.content[0].text)
```

**Streaming:**

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a haiku about coding"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

**System prompt:**

```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="You are a senior Python developer. Be concise.",
    messages=[{"role": "user", "content": "Review this function"}]
)
```

## TypeScript SDK

**Installation:**

```bash
npm install @anthropic-ai/sdk
```

**Basic message:**

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic(); // reads ANTHROPIC_API_KEY from env

const message = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [
    { role: "user", content: "Explain async/await in TypeScript" }
  ],
});
console.log(message.content[0].text);
```

**Streaming:**

```typescript
const stream = client.messages.stream({
  model: "claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Write a haiku" }],
});

for await (const event of stream) {
  if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
    process.stdout.write(event.delta.text);
  }
}
```

## Tool Use

Define tools and let Claude call them:

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }
]

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in SF?"}]
)

# Handle tool use response
for block in message.content:
    if block.type == "tool_use":
        result = get_weather(**block.input)
        # Send result back to continue the conversation
        follow_up = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=[
                {"role": "user", "content": "What's the weather in SF?"},
                {"role": "assistant", "content": message.content},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                ]}
            ]
        )
```

## Vision

Send images for analysis:

```python
import base64

with open("diagram.png", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
            {"type": "text", "text": "Describe this diagram"}
        ]
    }]
)
```

## Extended Thinking

For complex reasoning tasks where step-by-step thinking improves accuracy:

```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    messages=[{"role": "user", "content": "Solve this math problem step by step..."}]
)

for block in message.content:
    if block.type == "thinking":
        print(f"Thinking: {block.thinking}")
    elif block.type == "text":
        print(f"Answer: {block.text}")
```

## Prompt Caching

Cache large system prompts or context to reduce costs (up to 90% on cached tokens):

```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {"type": "text", "text": large_system_prompt, "cache_control": {"type": "ephemeral"}}
    ],
    messages=[{"role": "user", "content": "Question about the cached context"}]
)

# Check cache usage
print(f"Cache read: {message.usage.cache_read_input_tokens}")
print(f"Cache creation: {message.usage.cache_creation_input_tokens}")
```

## Batches API

Process large volumes asynchronously at 50% cost reduction:

```python
batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": f"request-{i}",
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
        }
        for i, prompt in enumerate(prompts)
    ]
)

# Poll for completion
import time
while True:
    status = client.messages.batches.retrieve(batch.id)
    if status.processing_status == "ended":
        break
    time.sleep(30)

# Get results
for result in client.messages.batches.results(batch.id):
    print(result.result.message.content[0].text)
```

## Agent SDK

Build multi-step agents with tool-use loops:

```python
# Note: Agent SDK API surface may change -- verify against current docs
import anthropic

tools = [{
    "name": "search_codebase",
    "description": "Search the codebase for relevant code",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
}]

client = anthropic.Anthropic()
messages = [{"role": "user", "content": "Review the auth module for security issues"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=tools,
        messages=messages,
    )
    if response.stop_reason == "end_turn":
        break
    # Handle tool calls and continue the loop
    messages.append({"role": "assistant", "content": response.content})
    # Execute tools and append tool_result messages
```

## Cost Optimization

| Strategy | Savings | When to Use |
|----------|---------|-------------|
| Prompt caching | Up to 90% on cached tokens | Repeated system prompts or context |
| Batches API | 50% | Non-time-sensitive bulk processing |
| Haiku instead of Sonnet | ~75% | Simple tasks, classification, extraction |
| Shorter max_tokens | Variable | When you know output will be short |
| Streaming | None (same cost) | Better UX, same price |

**Optimization priority:**

1. Use prompt caching for any system prompt or context reused across calls
2. Batch non-urgent work (reports, analysis, bulk classification)
3. Route simple tasks to Haiku (classification, extraction, formatting)
4. Reserve Opus for tasks that measurably benefit from deeper reasoning

## Error Handling

```python
import time
from anthropic import APIError, RateLimitError, APIConnectionError

try:
    message = client.messages.create(...)
except RateLimitError:
    # Back off and retry (429)
    time.sleep(60)
except APIConnectionError:
    # Network issue -- retry with exponential backoff
    pass
except APIError as e:
    # Other API errors (400, 401, 500, etc.)
    print(f"API error {e.status_code}: {e.message}")
```

**Rules:**

- Retry on `RateLimitError` (429) and `APIConnectionError` with exponential backoff
- Do not retry on `APIError` with 400/401/403 -- these indicate a code issue
- Set `ANTHROPIC_API_KEY` via environment variable, never hardcoded

## Environment Setup

```bash
# Required
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional: set default model
export ANTHROPIC_MODEL="claude-sonnet-4-6"
```

Never hardcode API keys. Always use environment variables or a secrets manager.

## Common Anti-Patterns

**Model selection:**

- Using Opus for simple extraction/classification -- 10x+ cost for no quality gain
- Hardcoding model IDs deep in application code instead of configuration
- Not benchmarking Haiku vs Sonnet for your specific use case

**Cost:**

- Not using prompt caching when the same system prompt is sent repeatedly
- Synchronous processing of bulk requests instead of using Batches API
- Setting max_tokens to 4096 when typical output is 200 tokens

**Tool use:**

- Not sending the `tool_result` back after tool execution -- conversation breaks
- Vague tool descriptions that cause Claude to misuse the tool
- Missing `required` fields in input_schema -- Claude guesses instead of asking

**Error handling:**

- Retrying on 400/401/403 in a loop -- these never self-resolve
- No backoff on rate limit errors -- makes the rate limiting worse
- Swallowing API errors silently instead of logging and alerting
