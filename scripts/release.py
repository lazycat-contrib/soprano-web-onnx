#!/usr/bin/env python3
"""Find the exact versioned Release asset for publication recovery."""
import json
import os
import re
import subprocess
from pathlib import Path

text = Path('package.yml').read_text()
package = re.search(r'^package: ([a-z0-9.]+)$', text, re.M).group(1)
version = re.search(r'^version: ([0-9]+\.[0-9]+\.[0-9]+)$', text, re.M).group(1)
repo = os.environ['GITHUB_REPOSITORY']
result = subprocess.run(['gh', 'api', f'repos/{repo}/releases/tags/v{version}'], capture_output=True, text=True)
outputs = {'exists': 'false', 'version': version}
if result.returncode:
    if '(HTTP 404)' not in result.stderr:
        raise SystemExit('Release lookup failed; refusing to rebuild after an unknown API error')
else:
    release = json.loads(result.stdout)
    name = f'{package}-v{version}.lpk'
    matches = [a for a in release['assets'] if a['name'] == name]
    if len(matches) > 1:
        raise SystemExit('Ambiguous Release assets')
    if matches:
        asset = matches[0]
        digest = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise SystemExit('Existing Release asset has no trusted SHA256 digest')
        url = f'https://github.com/{repo}/releases/download/v{version}/{name}'
        if asset['browser_download_url'] != url:
            raise SystemExit('Unexpected Release asset URL')
        outputs.update(exists='true', name=name, url=url, sha256=digest.removeprefix('sha256:'))
with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
    for key, value in outputs.items():
        output.write(f'{key}={value}\n')
print(f'Package {version}: ' + ('reuse verified Release asset' if outputs['exists'] == 'true' else 'build missing Release asset'))
