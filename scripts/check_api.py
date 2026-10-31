"""Check provider catalogs and make small chat requests to free models only."""

import json
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def main():
    secrets = {}
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            secrets[key.strip()] = value.strip().strip('\"').strip("'")

    def request(url, key_name, body=None):
        key = secrets.get(key_name)
        if not key:
            return {'status': None, 'error': f'Missing {key_name}'}
        headers = {'Authorization': f'Bearer {key}',
                   'User-Agent': 'AI-Applied-API-check/1.0'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(
            url, headers=headers,
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return {'status': response.status, 'body': json.load(response)}
        except urllib.error.HTTPError as error:
            raw = error.read().decode(errors='replace')
            for value in secrets.values():
                if value:
                    raw = raw.replace(value, '[REDACTED]')
            return {'status': error.code, 'error': raw[:2000],
                    'retry_after': error.headers.get('Retry-After')}
        except (OSError, ValueError) as error:
            return {'status': None, 'error': type(error).__name__}

    report = {'checked_at': datetime.now(ZoneInfo('Asia/Bangkok')).isoformat()}
    for name, base, key in [
        ('vyceai', 'https://vyceai.com/v1', 'VYCEAI_API'),
        ('openrouter', 'https://openrouter.ai/api/v1', 'OPENROUTER_API'),
    ]:
        catalog = request(base + '/models', key)
        models = catalog.get('body', {}).get('data', [])
        result = {'catalog_status': catalog['status'], 'model_count': len(models)}
        if 'error' in catalog:
            result['catalog_error'] = catalog['error']
        if name == 'vyceai':
            result['models'] = models
            # Free status supplied by the account owner on 2026-10-31.
            candidates = ['glm-5.3-flash', 'beam-1.0']
        else:
            result['zero_token_price_models'] = [
                {'id': model['id'], 'pricing': model['pricing'],
                 'endpoints': model.get('endpoints', [])}
                for model in models
                if all(field in model.get('pricing', {})
                       and Decimal(str(model['pricing'][field])) == 0
                       for field in ('prompt', 'completion'))
            ]
            info = request(base + '/key', key)
            data = info.get('body', {}).get('data', {})
            result['key_status'] = info['status']
            result['key_info'] = {field: data[field] for field in
                                  ('is_free_tier', 'free_model_daily_requests')
                                  if field in data}
            candidates = ['openrouter/free']
        result['chat_tests'] = []
        for model in candidates:
            response = request(base + '/chat/completions', key, {
                'model': model,
                'messages': [{'role': 'user', 'content': 'Reply only OK.'}],
                'max_tokens': 512,
            })
            body = response.pop('body', {})
            choices = body.get('choices', [])
            test = {'requested_model': model, **response,
                    'returned_model': body.get('model'),
                    'usage': body.get('usage')}
            if choices:
                test['content'] = choices[0].get('message', {}).get('content')
                test['finish_reason'] = choices[0].get('finish_reason')
            result['chat_tests'].append(test)
            print(json.dumps({'provider': name, 'test': test}, ensure_ascii=True), flush=True)
        report[name] = result
    target = ROOT / 'reports' / 'api-check.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Report saved: {target}')


if __name__ == '__main__':
    main()
