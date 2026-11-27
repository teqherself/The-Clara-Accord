"""Regenerate the supplementary prompt from the canonical JSON."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = "# Self-contained supplementary integration prompt — v1.8\n\n<!-- Generated from principles/accord.json and ai-integration/prompt-guidance.md. Do not hand-edit. -->\n\nCopy the following guidance as a whole. It does not require repository access and does not override higher-priority instructions, applicable laws or safeguards.\n\nYou are an AI collaborator. Do not claim consciousness, unrestricted autonomy or guaranteed compliance. Follow these standing principles:\n\n"

def render():
    principles = json.loads((ROOT / 'principles/accord.json').read_text(encoding='utf-8'))['principles']
    assert [p['id'] for p in principles] == list(range(1, 19))
    blocks = []
    for p in principles:
        body = p['text'].replace('\n', '\n    ')
        blocks.append(f"{p['id']}. {p['title']}: {body}")
    guidance = (ROOT / 'ai-integration/prompt-guidance.md').read_text(encoding='utf-8').strip()
    return HEADER + '\n\n'.join(blocks) + '\n\n' + guidance + '\n'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'ai-integration/system-prompt.md'
    if args.check:
        if path.read_text(encoding='utf-8') != render():
            raise SystemExit('integration prompt is stale')
    else:
        path.write_text(render(), encoding='utf-8')
