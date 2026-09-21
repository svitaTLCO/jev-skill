import urllib.request, json, time, re
from test_upgraded_harness import run_unit_test

task3_tests = """
assert validate_nested_tokens("()") == True, "Simple () failed"
assert validate_nested_tokens("([{}])") == True, "Nested failed"
assert validate_nested_tokens("([)]") == False, "Mismatched order failed"
assert validate_nested_tokens("('(')") == True, "Delimiter inside quotes failed - should be ignored!"
assert validate_nested_tokens('("]")') == True, "Closing bracket inside quotes failed - should be ignored!"
print("TEST_SUITE_SUCCESS")
"""

payload_bracket = {
    'model': 'huihui-qwen3.5:2b',
    'prompt': '<|im_start|>system\nYou are an expert python coder. Output clean code in markdown fences.<|im_end|>\n<|im_start|>user\nWrite a Python function validate_nested_tokens(s: str) -> bool that checks if parentheses (), brackets [], and braces {} are properly matched and closed in order. Also ignore any delimiters inside single quotes or double quotes.<|im_end|>\n<|im_start|>assistant\n<think>\n',
    'think': True,
    'options': {'num_predict': 1400, 'temperature': 0.1},
    'stream': False
}
req = urllib.request.Request('http://localhost:11434/api/generate', data=json.dumps(payload_bracket).encode(), headers={'Content-Type': 'application/json'})
t0 = time.perf_counter()
with urllib.request.urlopen(req, timeout=120) as r:
    res = json.loads(r.read())
t_gen = time.perf_counter() - t0
resp = res.get('response', '')
code = resp.split('</think>')[-1] if '</think>' in resp else resp
m = re.findall(r'```(?:python)?\s*\n?(.*?)(?:```|$)', code, re.DOTALL)
valid_c = m[0].strip() if m else code.strip()

passed, err = run_unit_test(valid_c, task3_tests)
print('THINKING MODE BRACKET RESULT:')
print(f'Time: {t_gen:.1f}s | Tokens: {res.get("eval_count")} | Passed: {passed}')
if not passed:
    print('Err:', err.splitlines()[-1] if err else '')
else:
    print('Code succeeded!')
