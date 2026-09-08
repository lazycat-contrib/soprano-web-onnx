#!/usr/bin/env python3
"""Assemble Release sources, verified model attachments and local browser runtimes."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

source = Path(sys.argv[1])
lock = json.loads(Path('upstream.json').read_text())
web = Path('content/web')
if web.exists():
    shutil.rmtree(web)
web.mkdir(parents=True)
for name in ('index.html', 'style.css', 'onnx-streaming.js', 'PCMPlayerWorklet.js', 'EventEmitter.js', 'README.md'):
    shutil.copy2(source / name, web / name)
if (source / 'LICENSE').exists():
    shutil.copy2(source / 'LICENSE', web / 'LICENSE')
else:
    # v0.1.0 declares Apache-2.0 in README but omitted the license text.
    # Fetch the upstream-added license from an immutable documentation commit.
    subprocess.run(['curl', '--fail', '--location', '--retry', '3',
        'https://raw.githubusercontent.com/KevinAHM/soprano-web-onnx/f7beaba96dcdb8b0492272fcb3a14ce2fc370da3/LICENSE',
        '-o', str(web / 'LICENSE')], check=True)
shutil.copytree(source / 'models/soprano-tokenizer', web / 'models/soprano-tokenizer')
for asset in lock['assets']:
    if not re.fullmatch(r'soprano_(backbone_kv|decoder)\.onnx(\.data)?', asset['name']):
        raise ValueError('Unexpected model name')
    pointer = (source / 'models' / asset['name']).read_text()
    if 'oid sha256:' + asset['sha256'] not in pointer or f"size {asset['size']}" not in pointer:
        raise ValueError('Source code and Release model disagree: ' + asset['name'])
    dest = web / 'models' / asset['name']
    subprocess.run(['curl', '--fail', '--location', '--retry', '3', asset['url'], '-o', str(dest)], check=True)
    with dest.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    if dest.stat().st_size != asset['size'] or digest != asset['sha256']:
        raise ValueError('Model checksum mismatch: ' + asset['name'])
    print('Verified Release model:', asset['name'], digest)

ort = Path('node_modules/onnxruntime-web')
ort_dest = web / 'vendor/ort'
ort_dest.mkdir(parents=True)
shutil.copy2(ort / 'dist/ort.all.min.js', ort_dest / 'ort.all.min.js')
for pattern in ('*.wasm', '*.mjs'):
    for path in (ort / 'dist').glob(pattern):
        shutil.copy2(path, ort_dest / path.name)
shutil.copy2(ort / 'README.md', ort_dest / 'README.md')
transformers = Path('node_modules/@huggingface/transformers')
transformers_dest = web / 'vendor/transformers'
transformers_dest.mkdir(parents=True)
shutil.copy2(transformers / 'dist/transformers.min.js', transformers_dest / 'transformers.min.js')
for package, dest in ((ort, ort_dest), (transformers, transformers_dest)):
    for pattern in ('LICENSE*', 'ThirdPartyNotices*'):
        for path in package.glob(pattern):
            if path.is_file():
                shutil.copy2(path, dest / path.name)

html_path = web / 'index.html'
html = html_path.read_text()
old = 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js'
if html.count(old) != 1:
    raise ValueError('Unexpected upstream runtime script')
html = html.replace(old, './vendor/ort/ort.all.min.js')
# Fonts are decorative; use the existing CSS fallback stack without remote requests.
html = '\n'.join(line for line in html.splitlines() if 'fonts.googleapis.com' not in line and 'fonts.gstatic.com' not in line) + '\n'
html_path.write_text(html)
js_path = web / 'onnx-streaming.js'
js = js_path.read_text()
old = 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.0'
if js.count(old) != 1:
    raise ValueError('Unexpected upstream tokenizer import; review the new Release before packaging')
js = js.replace(old, './vendor/transformers/transformers.min.js')
js = "ort.env.wasm.wasmPaths = new URL('./vendor/ort/', location.href).href;\nort.env.wasm.numThreads = 1;\n" + js
js_path.write_text(js)
# Walk the page entry's relative module graph and reject missing local imports.
visited = set()
pending = [web / 'onnx-streaming.js']
while pending:
    module = pending.pop().resolve()
    if module in visited:
        continue
    visited.add(module)
    if not module.is_relative_to(web.resolve()) or not module.is_file():
        raise ValueError('Missing or unsafe module dependency: ' + str(module))
    if 'vendor' in module.relative_to(web.resolve()).parts:
        continue
    text = module.read_text()
    for _, relative in re.findall(r"(?:from\s*|import\s*\()(['\"])(\.[^'\"]+)\1", text):
        pending.append(module.parent / relative.split('?')[0])
print('Verified local module dependencies:', len(visited))
shutil.copy2('upstream.json', 'content/upstream.json')
shutil.copy2('package-lock.json', 'content/runtime-package-lock.json')
print('Prepared Release', lock['tag'], 'with local models and runtimes')
