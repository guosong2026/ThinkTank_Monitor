#!/usr/bin/env python3
"""Test the same fetch and parser path used by scheduled monitoring, without writes or emails."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from monitor import MultiWebsiteMonitor
from website_configs import get_all_websites


def check_website(config):
    result = dict(name=config.name, url=config.url, status='unknown',
                  status_code=None, final_url=None, error=None, reports_found=0)
    monitor = MultiWebsiteMonitor([config], enable_email=False)

    def record_response(response, **kwargs):
        result.update(status_code=response.status_code, final_url=response.url)

    monitor.session.hooks['response'].append(record_response)
    try:
        html = monitor._fetch_page(config.url)
        if not html:
            result.update(status='fetch_failed', error='HTTP or network failure')
        else:
            reports = config.get_reports(html, config.url)
            result.update(reports_found=len(reports), reports=reports)
            result['status'] = 'success' if reports else 'empty'
            if not reports:
                result['error'] = 'Page accessible but no reports parsed'
    except Exception as exc:
        result.update(status='parse_error', error=str(exc))
    finally:
        monitor.session.close()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path, help='Write detailed results to this file')
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 9))
    args = parser.parse_args(argv)
    logging.getLogger().setLevel(logging.ERROR)
    websites = get_all_websites()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(check_website, websites))
    for result in results:
        print(f"{result['name']}: {result['status']} "
              f"(HTTP {result['status_code']}, reports={result['reports_found']})")
    success = sum(result['status'] == 'success' for result in results)
    print(f'Total: {len(results)}; passed: {success}; failed: {len(results) - success}')
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(dict(
            checked_at=datetime.now(timezone.utc).isoformat(),
            total=len(results), passed=success, results=results,
        ), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if success == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
