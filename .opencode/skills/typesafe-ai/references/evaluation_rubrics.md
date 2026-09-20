# Standard Code Quality Evaluation Rubrics for Jev

When evaluating code with Jev's `Score` primitive, use clear, distinct, and descriptive level criteria. Avoid ambiguous words like "good" or "bad"; describe the observable properties of the code at each level.

---

## 1. Code Maintainability & Readability Rubric (4-level Score)

```json
{
  "maintainability": {
    "type": "score",
    "instructions": "Rate the maintainability, readability, and modularity of the proposed code.",
    "criteria": [
      "Level 0 (Unacceptable): Monolithic spaghetti code, cryptic variable names, mixed abstraction layers, tightly coupled dependencies, no error handling.",
      "Level 1 (Needs Improvement): Understandable logic but brittle, copy-pasted patterns, missing comments on complex logic, minimal typing, or functions exceeding reasonable size.",
      "Level 2 (Solid): Clean structure, meaningful naming conventions, clear boundaries, appropriate modularization, idiomatic language patterns, and proper error propagation.",
      "Level 3 (Exemplary): Highly elegant, strictly decoupled, comprehensive type safety, self-documenting APIs, robust error handling, and fully aligned with modern best practices."
    ]
  }
}
```

---

## 2. Test Quality & Coverage Rubric (4-level Score)

```json
{
  "test_thoroughness": {
    "type": "score",
    "instructions": "Rate how thoroughly the test suite exercises the system's behavior and edge cases.",
    "criteria": [
      "Level 0: No assertions or trivial tests that only verify constructors or smoke tests.",
      "Level 1: Only tests the basic happy path. No negative testing, no boundary conditions, and no error handling tests.",
      "Level 2: Tests happy paths and primary error cases. Mocks are appropriately scoped and assertions verify output correctness.",
      "Level 3: Comprehensive testing including boundary values, empty inputs, network/timeout simulation, concurrent execution, and regression scenarios."
    ]
  }
}
```

---

## 3. Simplicity & Overengineering Rubric (3-level Score)

```json
{
  "simplicity": {
    "type": "score",
    "instructions": "Rate the simplicity of the solution compared to the complexity of the problem.",
    "criteria": [
      "Level 0 (Overengineered): Unnecessary layers of abstraction, premature generalization, excessive design patterns for simple tasks.",
      "Level 1 (Balanced): Appropriate complexity; provides just enough structure without gratuitous boilerplate.",
      "Level 2 (Minimalist): The simplest possible solution that completely satisfies all requirements and edge cases."
    ]
  }
}
```

---

## 4. Key Noul Checks for Safe Automated Coding

Combine these binary checks with scores in a single request:

| Question Key | Question Instructions | Red-Flag Threshold |
| :--- | :--- | :--- |
| `satisfies_all_requirements` | `"Does the proposed implementation completely fulfill all explicit and implicit requirements stated in the user prompt?"` | Reject/Iterate if `noul < 0.85` |
| `regression_risk` | `"Does this change introduce any risk of breaking existing functionality, mutating unrelated state, or breaking public API contracts?"` | Reject/Iterate if `noul > 0.20` |
| `security_risk` | `"Does the code introduce any security vulnerability such as injection, unsanitized user input, insecure deserialization, or exposed secrets?"` | Reject/Iterate if `noul > 0.15` |
| `handles_edge_cases` | `"Does the code properly guard against empty values, null pointers, missing parameters, and boundary conditions?"` | Reject/Iterate if `noul < 0.80` |
