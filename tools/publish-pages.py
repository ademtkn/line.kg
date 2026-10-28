#!/usr/bin/env python3
"""Build and push public files to gh-pages using existing Git authentication."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run(*args, cwd=ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)

run('python3', 'tools/pages.py')
remote = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, text=True).strip()
with tempfile.TemporaryDirectory(prefix='linekg-pages-') as temporary:
    target = Path(temporary)
    run('git', 'init', '--initial-branch=gh-pages', cwd=target)
    run('git', 'remote', 'add', 'origin', remote, cwd=target)
    existing = subprocess.check_output(['git', 'ls-remote', '--heads', remote, 'gh-pages'], cwd=ROOT, text=True)
    if existing:
        run('git', 'fetch', 'origin', 'gh-pages', cwd=target)
        run('git', 'reset', '--hard', 'FETCH_HEAD', cwd=target)
    for child in target.iterdir():
        if child.name != '.git':
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(ROOT / 'dist', target, dirs_exist_ok=True)
    run('git', 'add', '--all', cwd=target)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=target).returncode
    if not existing or changed:
        source = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
        run('git', '-c', 'user.name=ademtkn', '-c', 'user.email=ademtkn@users.noreply.github.com', 'commit', '-m', 'Publish GitHub Pages from ' + source, cwd=target)
        run('git', 'push', 'origin', 'HEAD:gh-pages', cwd=target)
    else:
        print('Public files are already current.')
