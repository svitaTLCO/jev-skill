from test_upgraded_harness import query_no_think, run_unit_test

task3_tests = """
assert validate_nested_tokens("()") == True, "Simple () failed"
assert validate_nested_tokens("([{}])") == True, "Nested failed"
assert validate_nested_tokens("([)]") == False, "Mismatched order failed"
assert validate_nested_tokens("('(')") == True, "Delimiter inside quotes failed - should be ignored!"
assert validate_nested_tokens('("]")') == True, "Closing bracket inside quotes failed - should be ignored!"
print("TEST_SUITE_SUCCESS")
"""

bad_code = '''import re

def validate_nested_tokens(s: str) -> bool:
    cleaned = re.sub(r'"[^"]*"|\'[^\']*\'', '', s)
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}
    for ch in cleaned:
        if ch in mapping.values():
            stack.append(ch)
        elif ch in mapping:
            if not stack or stack[-1] != mapping[ch]:
                return False
            stack.pop()
    return not stack
'''

heal_prompt = f"""Your code failed with a syntax error:
ERROR: SyntaxError: unterminated string literal

DEFECTIVE CODE:
```python
{bad_code}
```

INSTRUCTION: Fix the regex line using `re.sub(r'\"[^\"]*\"|\x27[^\x27]*\x27', '', s)` or `re.sub(r'\"[^\"]*\"|\'[^\']*\'', '', s)`.
Return ONLY the complete, compilable Python code inside markdown fences.
"""

healed, t, tok = query_no_think(heal_prompt)
passed, err = run_unit_test(healed, task3_tests)
print("=" * 60)
print("SELF-HEALED NO-THINK RESULT:")
print(f"Time: {t:.1f}s | Tokens: {tok} | Passed: {passed}")
if not passed:
    print("Err:", err)
else:
    print("🎉 100% UNIT TEST PASS!")
    print(healed)
print("=" * 60)
