"""Build the reproducible demo, prepare BigQuery inputs, or export live results."""
import argparse
import csv
import hashlib
import json
import random
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = 1604188800
DAY = 86400
CHANNELS = [
    ('Paid Search', 'brand'), ('Paid Social', 'prospecting'), ('Email', 'lifecycle'),
    ('Organic Search', '(unassigned)'), ('Direct', '(unassigned)'),
]
MODELS = (
    'identity_map', 'events_resolved', 'sessions', 'orders',
    'customer_profile', 'attribution', 'campaign_performance',
)
INPUTS = {
    'crm': ('customer_id:STRING', 'market:STRING'),
    'identify': ('anonymous_id:STRING', 'customer_id:STRING'),
    'app_events': ('anonymous_id:STRING', 'session_id:STRING', 'ts:INTEGER',
                   'event_name:STRING', 'order_id:STRING', 'revenue:FLOAT',
                   'channel:STRING', 'campaign:STRING'),
    'spend': ('spend_date:DATE', 'channel:STRING', 'campaign:STRING', 'cost_usd:FLOAT'),
}


def synthetic_inputs(aliases):
    """Pair selected web aliases with simulated CRM records and app devices."""
    rng = random.Random(360)
    crm, identify, app_events = [], [], []
    for index, alias in enumerate(aliases, start=1):
        key = f'c{index:05}'
        app = f'app:{key}'
        crm.append((key, rng.choice(('US', 'CA', 'GB'))))
        identify.extend([(alias, key), (app, key)])
        for visit in range(rng.randrange(1, 4)):
            ts = START + rng.randrange(4, 89) * DAY + 3600
            channel, campaign = rng.choice(CHANNELS)
            session = f'{app}:{visit}'
            app_events.append((app, session, ts, 'screen_view', None, 0, channel, campaign))
            if rng.random() < 0.20:
                app_events.append((app, session, ts + 180, 'in_app_purchase',
                                   f'{session}:order', rng.randrange(18, 160), None, None))
    return {'crm': crm, 'identify': identify, 'app_events': app_events, 'spend': []}


def local_data():
    rng = random.Random(92)
    aliases = [f'web:{index:04}' for index in range(480)]
    inputs = synthetic_inputs(aliases[:350])
    web = []
    for index, alias in enumerate(aliases):
        origin = rng.randrange(0, 60)
        for visit in range(rng.randrange(2, 7)):
            ts = START + (origin + visit * 5) * DAY + rng.randrange(3600, 7000)
            choices = (0, 1, 1, 3) if visit == 0 else (0, 2, 2, 3, 4)
            channel, campaign = CHANNELS[rng.choice(choices)]
            session = f'{alias}:{visit}'
            web.append((alias, session, ts, 'page_view', None, 0, channel, campaign))
            if visit and rng.random() < (0.45 if channel == 'Email' else 0.20):
                order = (alias, session, ts + 120, 'purchase', f'web-order:{index}:{visit}',
                         rng.randrange(18, 200), None, None)
                web.append(order)
                if index % 23 == 0:
                    web.append(order)
    inputs['identify'].append((aliases[0], 'c00002'))
    inputs['spend'] = [
        ('2021-01-01', channel, campaign, cost)
        for (channel, campaign), cost in zip(CHANNELS, (9100, 7300, 2200))
    ] + [('2021-01-01', 'Paid Social', 'unconverted', 450)]
    return inputs, web


def insert_rows(db, name, schema, rows):
    columns = ', '.join(field.replace(':', ' ') for field in schema)
    db.execute(f'create table {name} ({columns})')
    placeholders = ', '.join('?' for _ in schema)
    db.executemany(f'insert into {name} values ({placeholders})', rows)


def local_sql(path):
    sql = path.read_text(encoding='utf-8')
    sql = re.sub(r"{{ ref\('([\w]+)'\) }}", r'\1', sql)
    sql = re.sub(r"{{ source\('inputs', '([\w]+)'\) }}", r'\1', sql)
    return re.sub(r"{{ var\('[\w]+', ([\d.]+)\) }}", r'\1', sql)


def build_demo():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.create_function('concat', -1, lambda *parts: ''.join(parts) if None not in parts else None)
    db.create_function('power', 2, pow)
    db.create_function('floor', 1, lambda value: None if value is None else int(value // 1))
    inputs, web = local_data()
    for name, rows in inputs.items():
        insert_rows(db, name, INPUTS[name], rows)
    insert_rows(db, 'stg_events', INPUTS['app_events'], web + inputs['app_events'])
    for model in MODELS:
        sql = local_sql(ROOT / 'models' / f'{model}.sql')
        db.execute(f'create table {model} as {sql}')
        if model == 'sessions':
            db.execute('create index session_customer_time on sessions(customer_key, session_ts)')
    return db


def local_validation(db):
    for path in sorted((ROOT / 'warehouse_tests').glob('*.sql')):
        rows = db.execute(local_sql(path)).fetchall()
        assert not rows, f'{path.stem}: {len(rows)} failing rows'
        print(f'PASS {path.stem}')
    scalar = lambda sql: db.execute(sql).fetchone()[0]
    assert scalar("select count(*) from identity_map where identity_status = 'conflict'") == 1
    assert scalar("select count(distinct customer_key) from sessions where session_id like 'app:c00002:%' or session_id like 'web:0001:%'") == 1
    assert scalar("select count(*) from sessions where session_id like 'web:0000:%' and customer_key = 'anon:web:0000'") > 0
    assert scalar("select count(*) from stg_events where order_id is not null") > scalar('select count(*) from orders')
    assert scalar("select count(*) from campaign_performance where campaign = 'unconverted' and credited_revenue = 0 and roi = -1 and cpa is null") == 4
    assert scalar("select count(*) from campaign_performance where spend is null and (roi is not null or cpa is not null)") == 0
    assert scalar("select count(*) from attribution where channel = 'Unattributed'") == 0
    print('PASS conflict isolation, cross-device stitching, deduplication, spend-only campaigns, null ratios and journey coverage')
    return {table: scalar(f'select count(*) from {table}') for table in
            ('stg_events', 'sessions', 'orders', 'customer_profile', 'attribution')}


def export(rows, out, provenance, counts):
    out.mkdir(parents=True, exist_ok=True)
    names = ('campaign_performance', 'segments')
    data = {}
    for name in names:
        records = [dict(row) for row in rows[name]]
        data[name] = records
        if records:
            with (out / f'{name}.csv').open('w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
    data.update(provenance=provenance, counts=counts)
    payload = json.dumps(data, default=str).replace('<', r'\u003c')
    (out / 'data.js').write_text('window.C360 = ' + payload + ';\n', encoding='utf-8')


SEGMENTS = """select segment, count(*) as customers, sum(monetary) as revenue,
    avg(annualized_ltv_proxy) as avg_annualized_ltv
from {profile} group by segment order by customers desc, segment"""


def offline(output):
    with build_demo() as db:
        counts = local_validation(db)
        rows = {
            'campaign_performance': db.execute(
                'select * from campaign_performance order by model, channel, campaign'),
            'segments': db.execute(SEGMENTS.format(profile='customer_profile')),
        }
        export(rows, output, 'Synthetic offline demo', counts)
        print(json.dumps(counts))


def bigquery(args):
    from google.cloud import bigquery as bq

    for value in (args.project, args.inputs, args.dataset):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
            raise ValueError('Project and dataset identifiers must contain letters, numbers, hyphens or underscores.')
    client = bq.Client(project=args.project, location='US')
    job_config = bq.QueryJobConfig(maximum_bytes_billed=20_000_000_000)
    if args.mode == 'prepare':
        query = """
        select user_pseudo_id
        from `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
        where _TABLE_SUFFIX between '20201101' and '20210131'
          and event_name = 'purchase'
          and user_pseudo_id not in ('', '<Other>')
        group by user_pseudo_id
        order by farm_fingerprint(user_pseudo_id), user_pseudo_id
        limit 500
        """
        aliases = ['web:' + row.user_pseudo_id for row in client.query(query, job_config=job_config).result()]
        inputs = synthetic_inputs(aliases)
        # Planned app campaign costs. Web channel costs remain unknown.
        inputs['spend'] = [
            ('2021-01-01', channel, campaign, cost)
            for (channel, campaign), cost in zip(CHANNELS, (1300, 1050, 450))
        ]
        client.create_dataset(bq.Dataset(f'{args.project}.{args.inputs}'), exists_ok=True)
        for name, rows in inputs.items():
            fields = [field.split(':') for field in INPUTS[name]]
            schema = [bq.SchemaField(column, kind) for column, kind in fields]
            records = [dict(zip((field[0] for field in fields), row)) for row in rows]
            config = bq.LoadJobConfig(schema=schema, write_disposition='WRITE_TRUNCATE')
            table = f'{args.project}.{args.inputs}.{name}'
            client.load_table_from_json(records, table, job_config=config).result()
            print(f'{table}: {len(records)} rows')
        return
    prefix = f'{args.project}.{args.dataset}'
    queries = {
        'campaign_performance': f'select * from `{prefix}.campaign_performance` order by model, channel, campaign',
        'segments': SEGMENTS.format(profile=f'`{prefix}.customer_profile`'),
    }
    rows = {name: client.query(sql, job_config=job_config).result() for name, sql in queries.items()}
    counts = {name: client.get_table(f'{prefix}.{name}').num_rows for name in
              ('stg_events', 'sessions', 'orders', 'customer_profile', 'attribution')}
    export(rows, args.output, 'Public GA4 sample with simulated CRM, app activity and spend', counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['demo', 'prepare', 'export'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--project')
    parser.add_argument('--inputs', default='customer360_inputs')
    parser.add_argument('--dataset', default='customer360')
    args = parser.parse_args()
    if args.mode == 'demo':
        offline(args.output or ROOT / 'demo')
        return
    if not args.project:
        parser.error('--project is required for warehouse operations')
    if args.mode == 'export' and not args.output:
        parser.error('--output is required for warehouse exports')
    bigquery(args)


if __name__ == '__main__':
    main()
