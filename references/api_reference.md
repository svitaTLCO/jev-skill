# TypeSafe System One API Reference

## Base Endpoint
- **URL**: `https://api.typesafe.ai/v1/systemone`
- **Method**: `POST`
- **Headers**:
  - `Authorization: Bearer <TYPESAFE_API_KEY>`
  - `Content-Type: application/json`

---

## Request Schema

```json
{
  "state": "<string | object>",
  "model": "jev-latest",
  "questions": {
    "<question_id>": {
      "type": "choice | score | noul",
      "instructions": "<string | object>",
      "criteria": "<object | array>"
    }
  }
}
```

### Parameters
- **`state`** *(required, string or JSON)*: The subject context to evaluate. For coding tasks, structure this as markdown or JSON with the user requirements, code snippet/diff, and relevant file context.
- **`model`** *(optional, string)*: Model identifier. Default is `jev-latest`. Currently supported models include `jev-latest`, `jev-1.13`.
- **`questions`** *(required, map)*: A dictionary mapping code-friendly keys to question objects.

### Question Schemas

#### 1. Choice Question
```json
{
  "type": "choice",
  "instructions": "Which design pattern is best suited for this requirement?",
  "criteria": {
    "factory": "Use a factory pattern to encapsulate object creation logic.",
    "strategy": "Use a strategy pattern allowing dynamic interchange of algorithms.",
    "singleton": "Ensure single instance across entire runtime lifecycle."
  }
}
```

#### 2. Score Question
```json
{
  "type": "score",
  "instructions": "Evaluate the code maintainability.",
  "criteria": [
    "Level 0: Poor, tangled, high cognitive overhead, unreadable.",
    "Level 1: Understandable but fragile and lacking structure.",
    "Level 2: Good, clean, idiomatic, well-named.",
    "Level 3: Production excellence, modular, self-documenting."
  ]
}
```

#### 3. Noul Question
```json
{
  "type": "noul",
  "instructions": "Does this proposed code introduce any potential data loss or regression risk?"
}
```

---

## Response Schema

```json
{
  "model": "jev-latest",
  "answers": {
    "maintainability": {
      "type": "score",
      "score": 2.41,
      "legend": {
        "0": "Level 0...",
        "1": "Level 1...",
        "2": "Level 2...",
        "3": "Level 3..."
      },
      "confidence": 0.812
    },
    "has_regression": {
      "type": "noul",
      "noul": 0.082
    },
    "architecture_choice": {
      "type": "choice",
      "choice": "strategy",
      "probabilities": {
        "factory": 0.12,
        "strategy": 0.85,
        "singleton": 0.03
      },
      "confidence": 0.78
    }
  },
  "usage": {
    "input_tokens": 512,
    "output_tokens": 64
  }
}
```

---

## Error Handling & Status Codes

| Status Code | Error Meaning | Remediation |
| :--- | :--- | :--- |
| `400 BadRequest` | Malformed payload or invalid question structure | Verify question types (`choice`, `score`, `noul`) and criteria |
| `401 Unauthorized` | Missing or invalid API key | Set `TYPESAFE_API_KEY` in environment |
| `422 Unprocessable` | Semantic failure in criteria | Check score criteria array ordering or choice keys |
| `429 RateLimit` | Too many requests | Implement exponential backoff or batch questions in single calls |
| `500+ InternalError` | Service degradation | Retry with backoff |
