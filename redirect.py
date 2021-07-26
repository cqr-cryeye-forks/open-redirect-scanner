#!/usr/bin/env python
import argparse
import asyncio
import json
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import List

import requests
import urllib3

results: List[dict] = []


def url_generator(domains_path: str, payload_path: str):
    with open(domains_path) as d:
        with open(payload_path) as p:
            for domain in d:
                for payload in p:
                    yield f'https://{domain.strip()}{payload}'


def test_open_redirect(s: requests.Session, url: str):
    print(url)
    try:
        resp = s.get(url=url, timeout=10, verify=False)
        if not resp.history:
            return

        result = {
            'link': url,
            'link_code': resp.status_code,
            'data': []
        }
        for r in resp.history[:1]:
            result['data'].append({
                'result': 'Request was redirected',
                'link': r.url,
                'code': r.status_code
            })
        result['data'].append({
            'result': 'Final destination',
            'link': resp.url,
            'code': resp.status_code
        })
        results.append(result)
    except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError):
        pass


def shutdown():
    print('Graceful shutdown...')
    for task in asyncio.all_tasks():
        task.cancel()


async def main():
    # Payloads example
    # This is replaced with a payloads.list (a lot of amazing redirect payloads)
    # payload = '//www.google.com/%2F..'
    # payload2 = '//www.yahoo.com//'
    # payload3 = '//www.yahoo.com//%2F%2E%2E'

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', help='path to file of domain list', dest='domain', required=True)
    parser.add_argument('-w', help='payload wordlist', dest='payload', default='payloads.list')
    parser.add_argument('-o', help='output filename, default output.json', dest='output', default='output.json')
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    futures = []

    print('Searching the ex-girlfriend target & Holy Grail at [303 see others]...')

    # open file with subdomains and iterates
    # loop for find the trace of all requests (303 is an open redirect) see the final destination
    with requests.Session() as s:
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 1) as pool:
            for url in url_generator(domains_path=args.domain, payload_path=args.payload):
                futures.append(loop.run_in_executor(pool, test_open_redirect, s, url))

            for signame in {'SIGINT', 'SIGTERM'}:
                loop.add_signal_handler(getattr(signal, signame), shutdown)

            await asyncio.gather(*futures)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=3)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except asyncio.exceptions.CancelledError:
        pass
