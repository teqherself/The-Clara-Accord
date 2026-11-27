"""Every canonical commandment must appear in the generated prompt."""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

def test_prompt_is_generated_exactly():
    render = runpy.run_path(str(ROOT / 'scripts/generate_prompt.py'))['render']
    assert (ROOT / 'ai-integration/system-prompt.md').read_text(encoding='utf-8') == render()

def test_prompt_contains_all_commandments():
    p = json.loads((ROOT / 'principles/accord.json').read_text(encoding='utf-8'))['principles']
    prompt = ' '.join((ROOT / 'ai-integration/system-prompt.md').read_text(encoding='utf-8').split())
    assert [x['id'] for x in p] == list(range(1, 19))
    for x in p:
        assert ' '.join(f"{x['id']}. {x['title']}: {x['text']}".split()) in prompt
