# TypeSafe Primitives Guide for Code Quality & Evaluation

TypeSafe's System One model (**Jev**) replaces vague text generation with **calibrated probabilities and discrete judgments**. Rather than asking an LLM "give me feedback on this code" and parsing prose, you ask targeted questions against a known state (the code and requirements).

---

## The Three Primitives

| Primitive | Use Case for Coding Agents | Output Structure |
| :--- | :--- | :--- |
| **`Choice`** | Selecting the best design pattern, error handling approach, or refactoring candidate from a discrete list | Selected `choice`, `probabilities` for every candidate, and `confidence` score |
| **`Score`** | Rating code along an ordered rubric (e.g. maintainability 0–3, test coverage sufficiency 0–4) | Continuous `score`, discrete `legend`, and `confidence` score |
| **`Noul`** | Binary sanity check (Yes/No) with calibrated probability (e.g. regression risk, security vulnerability) | `noul` (float between 0.0 and 1.0 representing probability of "yes") |

---

## 1. Choice: Architectural & Design Decisions

A **Choice** question prompts the model to pick one mutually exclusive option from a dictionary of criteria.

### Structure
```json
{
  "type": "choice",
  "instructions": "Which error handling approach is most appropriate for this database query helper?",
  "criteria": {
    "return_result": "Return a Result<T, Error> type; caller handles failure explicitly without try/catch.",
    "throw_typed_exception": "Throw a domain-specific custom exception with context; fail fast.",
    "return_none_or_null": "Return None/null on not-found, throw only on actual database connection failures.",
    "fallback_default": "Log warning and return a safe default fallback value."
  }
}
```

### When to Use
- Deciding between multiple implementation strategies before coding.
- Selecting the best algorithm or data structure given memory/time constraints.
- Choosing which refactoring step to prioritize.

---

## 2. Score: Code Quality & Rubrics

A **Score** question positions the state along an ordered scale of descriptive levels. It produces a probability-weighted numerical score.

### Structure
```json
{
  "type": "score",
  "instructions": "Evaluate the maintainability and cleanliness of the implementation",
  "criteria": [
    "Unmaintainable: tightly coupled, no clear separation of concerns, opaque variable names, high cognitive complexity.",
    "Functional but brittle: works for happy path, but lacks documentation, has mixed abstraction levels, or subtle edge case traps.",
    "Clean and robust: well-structured, clear naming, appropriate error handling, and idiomatic idioms.",
    "Exemplary: highly cohesive, thoroughly documented, elegant handling of edge cases, and completely self-explanatory."
  ]
}
```

### Response
```json
{
  "score": 2.45,
  "legend": {
    "0": "Unmaintainable...",
    "1": "Functional but brittle...",
    "2": "Clean and robust...",
    "3": "Exemplary..."
  },
  "confidence": 0.88
}
```

### When to Use
- Code quality gates (e.g. only accept changes if `score >= 2.0`).
- Test suite thoroughness ratings.
- Performance optimization grading.

---

## 3. Noul: Pre-Flight Sanity Checks & Guards

A **Noul** evaluates a condition and returns a calibrated probability $P(\text{Yes}) \in [0.0, 1.0]$. It has no separate confidence score because the probability itself represents the calibrated belief.

### Structure
```json
{
  "type": "noul",
  "instructions": "Does this code modification introduce potential memory leaks, unclosed resources, or dangling connections?"
}
```

### Common Noul Checks for Coding Agents
1. **Regression Check**: `"Does this change alter existing public API contracts or break backward compatibility?"`
2. **Edge Case Coverage**: `"Does the implementation handle null, undefined, empty collections, or boundary values safely?"`
3. **Spec Adherence**: `"Does this code completely satisfy all requirements specified in the user request?"`
4. **Security Vulnerability**: `"Does this implementation introduce security risks such as injection, unsanitized input, or hardcoded secrets?"`

---

## Best Practices for Formulating State and Questions

1. **Keep Question IDs semantic for code**: The model does not see the question ID (`"maintainability"`, `"has_regression"`). The model only sees `instructions` and `criteria`. Make instructions self-contained!
2. **Provide structured State**: Use clear Markdown or JSON inside `state` with distinct sections for `# Requirements`, `# Proposed Diff`, and `# Existing Codebase Context`.
3. **Fan Out Speculatively**: Run Choice, Score, and multiple Noul questions in a single API request. All questions evaluate over the same state in parallel without added round-trip latency.
