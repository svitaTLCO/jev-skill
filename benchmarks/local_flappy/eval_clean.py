import json, urllib.request, subprocess, os

def get_key():
    res = subprocess.run(['security', 'find-generic-password', '-s', 'network-infra-typesafe-jev', '-w'], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else os.environ.get('TYPESAFE_API_KEY')

with open('benchmarks/local_flappy/jev_micro_game.html') as f:
    full_html = f.read()

payload = {
    'state': '## Complete HTML Game File\n\n' + full_html,
    'model': 'jev-latest',
    'questions': {
        'is_complete_and_playable': {
            'type': 'noul',
            'instructions': 'Is this HTML file complete, syntactically valid Javascript, and immediately playable in a browser?'
        },
        'code_quality': {
            'type': 'score',
            'instructions': 'Rate code structure, modularity, and cleanliness',
            'criteria': [
                'Broken / Non-functional / Repetitive loop',
                'Fragile / Partially working',
                'Clean, working, well-structured',
                'Exemplary production-grade'
            ]
        }
    }
}

req = urllib.request.Request(
    'https://api.typesafe.ai/v1/systemone',
    data=json.dumps(payload).encode(),
    headers={'Authorization': f'Bearer {get_key()}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
    print('Jev Evaluation on jev_micro_game.html:')
    print(json.dumps(data['answers'], indent=2))
