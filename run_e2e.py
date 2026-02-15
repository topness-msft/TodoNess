"""Run E2E tests and log results to manifest.json for the dashboard."""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def get_next_run_id():
    """Determine the next run ID from manifest.json."""
    manifest_path = PROJECT_ROOT / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
        runs = data.get('test_runs', [])
        if runs:
            last_id = runs[-1].get('id', 'run-000')
            num = int(last_id.split('-')[1]) + 1
            return f'run-{num:03d}'
    return 'run-001'


def parse_pytest_output(output: str):
    """Parse pytest output for pass/fail/skip counts."""
    # Match patterns like "5 passed", "2 failed", "1 skipped"
    passed = 0
    failed = 0
    skipped = 0

    match = re.search(r'(\d+) passed', output)
    if match:
        passed = int(match.group(1))
    match = re.search(r'(\d+) failed', output)
    if match:
        failed = int(match.group(1))
    match = re.search(r'(\d+) skipped', output)
    if match:
        skipped = int(match.group(1))

    total = passed + failed + skipped
    status = 'passed' if failed == 0 and total > 0 else 'failed'
    return total, passed, failed, skipped, status


def build_timeline(run_dir: Path):
    """Build timeline from screenshots."""
    timeline = []
    now = datetime.now(timezone.utc)
    timeline.append({
        'type': 'info',
        'timestamp': now.isoformat(),
        'message': 'Starting E2E test suite'
    })

    screenshots_dir = run_dir / 'screenshots'
    if screenshots_dir.exists():
        for f in sorted(screenshots_dir.iterdir()):
            if f.suffix in ('.png', '.jpg'):
                name = f.stem.replace('-', ' ').replace('_', ' ')
                timeline.append({
                    'type': 'screenshot',
                    'timestamp': now.isoformat(),
                    'message': name,
                    'path': f'test-runs/{run_dir.name}/screenshots/{f.name}'
                })

    timeline.append({
        'type': 'info',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'message': 'E2E test suite completed'
    })
    return timeline


def main():
    run_id = get_next_run_id()
    run_dir = PROJECT_ROOT / 'test-runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f'Running E2E tests: {run_id}')

    # Run pytest
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/e2e/', '-v', '-s', '--browser', 'chromium'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + '\n' + result.stderr

    # Save logs
    logs_path = run_dir / 'logs.txt'
    with open(logs_path, 'w') as f:
        f.write(output)

    print(output)

    # Copy screenshots
    src_screenshots = PROJECT_ROOT / 'test-runs' / 'playwright-screenshots'
    if src_screenshots.exists():
        dst_screenshots = run_dir / 'screenshots'
        if dst_screenshots.exists():
            shutil.rmtree(dst_screenshots)
        shutil.copytree(src_screenshots, dst_screenshots)

    # Copy video (take the first one)
    src_videos = PROJECT_ROOT / 'test-runs' / 'playwright-videos'
    if src_videos.exists():
        videos = list(src_videos.glob('*.webm'))
        if videos:
            shutil.copy2(videos[0], run_dir / 'recording.webm')

    # Parse results
    total, passed, failed, skipped, status = parse_pytest_output(output)
    print(f'\nResults: {total} total, {passed} passed, {failed} failed, {skipped} skipped -> {status}')

    # Build timeline
    timeline = build_timeline(run_dir)

    # Update manifest
    manifest_path = PROJECT_ROOT / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {'test_runs': []}

    now = datetime.now(timezone.utc).isoformat()
    video_path = f'test-runs/{run_id}/recording.webm' if (run_dir / 'recording.webm').exists() else None

    entry = {
        'id': run_id,
        'name': f'E2E Dashboard Tests ({run_id})',
        'status': status,
        'timestamp': now,
        'tests_total': total,
        'tests_passed': passed,
        'tests_failed': failed,
        'tests_skipped': skipped,
        'timeline': timeline,
    }
    if video_path:
        entry['video'] = video_path

    manifest['test_runs'].append(entry)

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f'\nManifest updated. View in dashboard Test Review tab.')
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
