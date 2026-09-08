#!/usr/bin/env python3
"""Follow the newest upstream Release, keeping its version and tag unchanged."""
import json
import os
import re
import subprocess
from pathlib import Path

REPO = 'KevinAHM/soprano-web-onnx'
MODELS = ('soprano_backbone_kv.onnx', 'soprano_decoder.onnx', 'soprano_decoder.onnx.data')


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def select_release():
    release = api(f'repos/{REPO}/releases/latest')
    tag = release['tag_name']
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag):
        raise ValueError('Expected upstream release tag vMAJOR.MINOR.PATCH')
    commit = api(f'repos/{REPO}/commits/{tag}')['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid release commit')
    assets = []
    for name in MODELS:
        matches = [a for a in release['assets'] if a['name'] == name]
        if len(matches) != 1:
            raise ValueError(f'Release must contain exactly one {name}')
        asset = matches[0]
        digest = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ValueError(f'Missing trusted SHA256 for {name}')
        url = f'https://github.com/{REPO}/releases/download/{tag}/{name}'
        if asset['browser_download_url'] != url or asset['size'] <= 0:
            raise ValueError(f'Invalid release asset: {name}')
        assets.append(dict(name=name, url=url, sha256=digest[7:], size=asset['size']))
    return dict(repository=REPO, tag=tag, version=tag[1:], commit=commit, assets=assets)


def main():
    selected = select_release()
    path = Path('upstream.json')
    if path.exists():
        previous = json.loads(path.read_text())
        if selected['tag'] == previous['tag'] and selected != previous:
            raise ValueError('Existing upstream Release changed; refusing to overwrite the published version')
    package = Path('package.yml')
    text = package.read_text()
    current = re.search(r'^version: (\d+\.\d+\.\d+)$', text, re.M).group(1)
    if tuple(map(int, selected['version'].split('.'))) < tuple(map(int, current.split('.'))):
        raise ValueError('Refusing version downgrade')
    path.write_text(json.dumps(selected, indent=2) + '\n')
    package.write_text(re.sub(r'^version: .*$', 'version: ' + selected['version'], text, count=1, flags=re.M))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('version=' + selected['version'] + '\n')
    print('Selected upstream Release ' + selected['tag'] + ' at ' + selected['commit'])


if __name__ == '__main__':
    main()
