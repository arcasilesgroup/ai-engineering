# Handler: X (Twitter) API Integration

## Purpose

Programmatic interaction with X (Twitter) for posting tweets, threads, reading timelines, searching content, uploading media, and handling rate limits. Covers OAuth authentication patterns, error handling, and security rules.

## Activation

Dispatched when the write skill involves X/Twitter integration: posting tweets, reading timelines, searching content, building bots, or any reference to "tweet", "X API", or "Twitter API".

## Procedure

### Step 1 -- Choose Authentication Method

**OAuth 2.0 (Bearer Token)** -- for read-heavy operations, search, public data:

```bash
export X_BEARER_TOKEN="your-bearer-token"
```

```python
import os
import requests

bearer = os.environ["X_BEARER_TOKEN"]
headers = {"Authorization": f"Bearer {bearer}"}
```

**OAuth 1.0a (User Context)** -- required for posting tweets, managing account, DMs:

```bash
export X_API_KEY="your-api-key"
export X_API_SECRET="your-api-secret"
export X_ACCESS_TOKEN="your-access-token"
export X_ACCESS_SECRET="your-access-secret"
```

```python
import os
from requests_oauthlib import OAuth1Session

oauth = OAuth1Session(
    os.environ["X_API_KEY"],
    client_secret=os.environ["X_API_SECRET"],
    resource_owner_key=os.environ["X_ACCESS_TOKEN"],
    resource_owner_secret=os.environ["X_ACCESS_SECRET"],
)
```

Decision guide:
- Reading public data only -> OAuth 2.0 Bearer
- Posting, replying, managing account -> OAuth 1.0a
- Both reading and writing -> OAuth 1.0a (superset)

### Step 2 -- Post a Tweet

```python
resp = oauth.post(
    "https://api.x.com/2/tweets",
    json={"text": "Hello from the API"}
)
resp.raise_for_status()
tweet_id = resp.json()["data"]["id"]
```

Single tweet limit: 280 characters. Validate length before posting.

### Step 3 -- Post a Thread (Reply Chain)

```python
def post_thread(oauth, tweets: list[str]) -> list[str]:
    """Post a thread by chaining replies. Returns list of tweet IDs."""
    ids = []
    reply_to = None
    for text in tweets:
        payload = {"text": text}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        resp = oauth.post("https://api.x.com/2/tweets", json=payload)
        resp.raise_for_status()
        tweet_id = resp.json()["data"]["id"]
        ids.append(tweet_id)
        reply_to = tweet_id
    return ids
```

Each tweet in the thread is a reply to the previous one. If any post fails mid-thread, return the IDs of successfully posted tweets for cleanup.

### Step 4 -- Read User Timeline

```python
resp = requests.get(
    f"https://api.x.com/2/users/{user_id}/tweets",
    headers=headers,
    params={
        "max_results": 10,
        "tweet.fields": "created_at,public_metrics",
    }
)
```

### Step 5 -- Search Tweets

```python
resp = requests.get(
    "https://api.x.com/2/tweets/search/recent",
    headers=headers,
    params={
        "query": "from:username -is:retweet",
        "max_results": 10,
        "tweet.fields": "public_metrics,created_at",
    }
)
```

### Step 6 -- Get User by Username

```python
resp = requests.get(
    "https://api.x.com/2/users/by/username/target_username",
    headers=headers,
    params={"user.fields": "public_metrics,description,created_at"}
)
```

### Step 7 -- Upload Media and Post

Media upload uses the v1.1 endpoint, then attach to a v2 tweet:

```python
# Step 1: Upload media (v1.1)
media_resp = oauth.post(
    "https://upload.twitter.com/1.1/media/upload.json",
    files={"media": open("image.png", "rb")}
)
media_id = media_resp.json()["media_id_string"]

# Step 2: Post tweet with media (v2)
resp = oauth.post(
    "https://api.x.com/2/tweets",
    json={"text": "Check this out", "media": {"media_ids": [media_id]}}
)
```

### Step 8 -- Rate Limit Management

**Rate limits reference**:

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /2/tweets | 200 | 15 min |
| GET /2/tweets/search/recent | 450 | 15 min |
| GET /2/users/:id/tweets | 1500 | 15 min |
| GET /2/users/by/username | 300 | 15 min |
| POST media/upload | 415 | 15 min |

**Inspect rate limit headers on every response**:

```python
import time

remaining = int(resp.headers.get("x-rate-limit-remaining", 0))
reset_at = int(resp.headers.get("x-rate-limit-reset", 0))

if remaining < 5:
    wait = max(0, reset_at - int(time.time()))
    print(f"Rate limit approaching. Resets in {wait}s")
```

### Step 9 -- Error Handling

```python
resp = oauth.post("https://api.x.com/2/tweets", json={"text": content})

if resp.status_code == 201:
    return resp.json()["data"]["id"]
elif resp.status_code == 429:
    reset = int(resp.headers["x-rate-limit-reset"])
    raise RateLimitError(f"Rate limited. Resets at {reset}")
elif resp.status_code == 403:
    raise PermissionError(
        f"Forbidden: {resp.json().get('detail', 'check permissions')}"
    )
else:
    raise APIError(f"X API error {resp.status_code}: {resp.text}")
```

Handle these status codes:
- **201**: Success (tweet created)
- **429**: Rate limited -- back off until `x-rate-limit-reset`
- **403**: Permission denied -- check token scopes and app permissions
- **401**: Authentication failed -- verify credentials
- **400**: Bad request -- validate payload before sending

## Output Format

Generated code includes:
- Authentication setup (env vars, OAuth session)
- API interaction functions with proper error handling
- Rate limit inspection on every response
- No hardcoded tokens anywhere in source

## Quality Gate

- All tokens sourced from environment variables -- zero hardcoded credentials
- `.env` files listed in `.gitignore`
- Rate limit headers inspected after every API call
- Error handling covers 201, 429, 403, 401, 400 status codes
- Tweet text validated against 280-character limit before posting
- Thread posting includes partial-failure recovery (return posted IDs)
- Media upload uses v1.1 endpoint; tweet creation uses v2 endpoint
