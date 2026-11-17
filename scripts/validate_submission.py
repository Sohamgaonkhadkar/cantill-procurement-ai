"""Validate evaluator export structure without calculating procurement decisions.

Only reads local files. Does not call an API, change policy, approve purchases,
rewrite outputs or copy assessment inputs into the public repository.
"""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
import argparse
import csv
import json
import re

from backend.domain import INPUT_COLUMNS, OUTPUT_COLUMNS

PREFERRED_COLUMNS = ['item_code', 'rank', 'supplier_id', 'reference_price']
PO_ROUTES = {'CONTRACT_PO', 'EMERGENCY_PO', 'SPOT_PO'}
SOURCING_ROUTES = {'RFQ', 'RFP', 'CAPEX_SOURCING', 'NEW_ITEM_SOURCING'}


def load(path, columns, exact=True):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source, strict=True)
        try:
            headers = reader.fieldnames or []
        except csv.Error as exc:
            raise ValueError(f'{Path(path).name}: Malformed CSV header') from exc
        if (headers != columns if exact else not set(columns) <= set(headers)):
            raise ValueError(f'{Path(path).name}: unexpected CSV headers')
        if len(set(headers)) != len(headers):
            raise ValueError(f'{Path(path).name}: duplicate CSV headers')
        try:
            rows = list(reader)
        except csv.Error as exc:
            raise ValueError(f'{Path(path).name}: Malformed CSV content') from exc
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f'{Path(path).name}: malformed CSV row width')
    return [{key: value.strip() for key, value in row.items()} for row in rows]


def decimal(value, label):
    if not re.fullmatch(r'\d+(?:\.\d+)?', value):
        raise ValueError(f'{label}: expected plain decimal text')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'{label}: invalid decimal') from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f'{label}: expected finite nonnegative decimal')
    return result


def validate(input_path, run1_path, run2_path, preferred_path, amended_version, suppliers_path=None, run1_snapshot=None, run2_snapshot=None, masters_snapshot=None, preferred_metadata=None):
    from .submission_semantics import read,validate_snapshot,ranking,cents
    snapshots={key:read(path) for key,path in [('run1',run1_snapshot),('run2',run2_snapshot)] if path}
    master=read(masters_snapshot) if masters_snapshot else None
    warnings=[];semantic={}
    inputs = load(input_path, INPUT_COLUMNS, exact=False)
    if not inputs:
        raise ValueError('Input batch is empty')
    identities = Counter((row['pr_no'], row['pr_line']) for row in inputs)
    plants = {(row['pr_no'], row['pr_line']): row['plant'] for row in inputs}
    active = None
    if suppliers_path:
        suppliers = load(suppliers_path, ['supplier_id', 'status'], exact=False)
        active = {row['supplier_id'] for row in suppliers if row['status'] == 'Active'}

    def eligible(supplier):
        if active is not None and supplier not in active:
            raise ValueError('Export contains an unknown or non-Active supplier')

    summary = {}
    for label, path, version in [('run1', run1_path, '5.0'), ('run2', run2_path, amended_version)]:
        rows = load(path, OUTPUT_COLUMNS)
        captured=snapshots.get(label)
        expected_versions={tuple((r['pr_no'],r['pr_line'])):r['policy_version'] for r in captured['rows']} if captured else None
        if Counter((row['pr_no'], row['pr_line']) for row in rows) != identities:
            raise ValueError(f'{label}: output PR-line identities/multiplicities differ from input')
        groups, orders = {}, {}
        for index, row in enumerate(rows, 1):
            where = f'{label} row {index}'
            expected_version=expected_versions[(row['pr_no'],row['pr_line'])] if expected_versions else version
            route = row['route']
            if not row['reason']:
                raise ValueError(f'{where}: decision reason is required')
            if row['policy_version'] and row['policy_version'] != expected_version:
                raise ValueError(f'{where}: wrong policy version; expected {version}')
            if route == 'NOT_PROCESSED':
                if any(row[key] for key in ['decision', 'po_id', 'supplier_id', 'unit_price', 'suggested_supplier_ids']):
                    raise ValueError(f'{where}: NOT_PROCESSED must not contain a purchasing action')
                continue
            if route not in PO_ROUTES | SOURCING_ROUTES:
                raise ValueError(f'{where}: unknown route')
            if row['policy_version'] != expected_version:
                raise ValueError(f'{where}: wrong policy version; expected {version}')
            if not row['group_id'] or not row['resolved_item_code']:
                raise ValueError(f'{where}: missing resolved item or requirement ID')
            decimal(row['group_value_inr'], where + ' group value')
            signature = (plants[(row['pr_no'], row['pr_line'])],) + tuple(row[key] for key in OUTPUT_COLUMNS if key not in {'pr_no', 'pr_line'})
            previous = groups.setdefault(row['group_id'], signature)
            if previous != signature:
                raise ValueError(f'{where}: inconsistent repeated requirement evidence')
            suggested = list(filter(None, row['suggested_supplier_ids'].split(';')))
            if len(suggested) != len(set(suggested)):
                raise ValueError(f'{where}: duplicate suggested supplier')
            for supplier in suggested:
                eligible(supplier)
            if route in PO_ROUTES:
                if row['decision'] != 'PO' or not row['po_id'] or not row['supplier_id'] or suggested:
                    raise ValueError(f'{where}: inconsistent PO fields')
                decimal(row['unit_price'], where + ' unit price')
                eligible(row['supplier_id'])
                order_signature = row['supplier_id'], plants[(row['pr_no'], row['pr_line'])], route
                if orders.setdefault(row['po_id'], order_signature) != order_signature:
                    raise ValueError(f'{where}: consolidated PO mixes suppliers/plants/routes')
            elif row['decision'] != 'SOURCING_REQUEST' or any(row[key] for key in ['po_id', 'supplier_id', 'unit_price']):
                raise ValueError(f'{where}: inconsistent sourcing fields')
            if route == 'NEW_ITEM_SOURCING' and (row['resolved_item_code'] != 'NEW' or suggested):
                raise ValueError(f'{where}: new item must have NEW code and no invented suggestions')
        summary[label] = {'rows': len(rows), 'requirements': len(groups), 'planned_pos': len(orders),
                          'routes': dict(sorted(Counter(row['route'] for row in rows).items()))}
        if captured:semantic[label]=validate_snapshot(inputs,rows,captured,master)
        else:warnings.append(label+': provide --'+label+'-snapshot for independent grouping, valuation, consolidation, date and hash checks')
    preferred = load(preferred_path, PREFERRED_COLUMNS)
    rankings = defaultdict(list)
    for index, row in enumerate(preferred, 1):
        if not row['item_code'] or not row['supplier_id'] or not row['rank'].isdigit() or not 1<=int(row['rank'])<=1000:
            raise ValueError(f'Preferred row {index}: invalid item, supplier or top-three rank')
        decimal(row['reference_price'], f'Preferred row {index} reference price')
        eligible(row['supplier_id'])
        rankings[row['item_code']].append((int(row['rank']), row['supplier_id']))
    for ranks in rankings.values():
        if sorted(rank for rank, _ in ranks) != list(range(1, len(ranks) + 1)) or len({sid for _, sid in ranks}) != len(ranks):
            raise ValueError('Preferred export has duplicate suppliers or non-contiguous ranks')
    if len(snapshots)==2 and snapshots['run1']['input_hash']!=snapshots['run2']['input_hash']:raise ValueError('Run 1 and Run 2 input hashes differ')
    if not master:warnings.append('No master snapshot: source prices, supplier eligibility, contract ceilings and rank order are not fully verified')
    if preferred_metadata and master:
        metadata=read(preferred_metadata);asof=metadata['as_of'];version=metadata['policy_version']
        policy=next((p for snap in snapshots.values() for p in snap['policy_snapshots'] if p['version']==version),None)
        supplied=metadata.get('policy_snapshot')
        if supplied:
            if supplied.get('version')!=version or supplied.get('status') not in {'active','superseded'}:raise ValueError('Preferred policy snapshot must identify the requested published version')
            keys=['version','effective_date','parameters','rules']
            if policy and any(policy[key]!=supplied[key] for key in keys):raise ValueError('Preferred policy snapshot conflicts with the captured run policy')
            policy=policy or supplied
        if not policy:raise ValueError('Provide the preferred policy_snapshot in metadata when the ranking version was unused by both captured runs')
        if policy['effective_date']>asof:raise ValueError('Preferred as-of date precedes policy effective date')
        expected=[]
        for item in sorted(master['items']):
            for rank,(sid,_,price) in enumerate(ranking(master,item,asof,policy)[:policy['parameters']['preferred_count']],1):expected.append({'item_code':item,'rank':str(rank),'supplier_id':sid,'reference_price':cents(price)})
        if preferred!=expected:raise ValueError('Preferred export differs from independent as-of/policy ranking and reference prices')
    else:warnings.append('Preferred as-of date/policy cannot be proven from CSV alone: provide --preferred-metadata and --masters-snapshot with both run snapshots')
    return {'valid': True, **summary, 'preferred_rows': len(preferred), 'preferred_items': len(rankings),
            'supplier_status_checked': active is not None or master is not None,
            'semantic_checks':semantic,'warnings':warnings,'failures':[],
            'scope': 'Read-only export and selected independent invariants; does not certify natural-language policy meaning or unknown blind-test accuracy'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'run1', 'run2', 'preferred', 'amended-version']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--suppliers', help='Private supplier master CSV; verifies Active status if supplied')
    for name in ['run1-snapshot','run2-snapshot','masters-snapshot','preferred-metadata']:
        parser.add_argument('--'+name,help='Private JSON evidence file; never committed or modified by this checker')
    args = parser.parse_args()
    try:
        result = validate(args.input, args.run1, args.run2, args.preferred, args.amended_version, args.suppliers,args.run1_snapshot,args.run2_snapshot,args.masters_snapshot,args.preferred_metadata)
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, StopIteration, InvalidOperation) as exc:
        parser.exit(1, json.dumps({'valid':False,'failures':[str(exc) or 'Malformed or incomplete evidence'],'warnings':[]})+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
