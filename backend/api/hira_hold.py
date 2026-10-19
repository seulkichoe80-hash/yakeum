"""TASK D MVP v2 guard. No mutation, representative selection or external I/O."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from backend.services.reconciliation.b_integration import _prepare_batch, reconcile_normalization_results
from backend.services.reconciliation.current_intake import build_current_intake_states
from backend.services.reconciliation.engine import _identity_rank

RAW_FIELDS = frozenset({'product_name', 'drug_code', 'date', 'dispensing_date',
                        'ingredient', 'strength', 'unit', 'dose_per_time',
                        'times_per_day', 'total_days'})


def _decimal_known(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        return Decimal(str(value)).is_finite()
    except (InvalidOperation, ValueError):
        return False


def _comparable(record):
    ingredients = record.get('ingredients') or []
    return bool(
        (record.get('mfds_product_id') or record.get('drug_code') or record.get('product_name_normalized'))
        and ingredients
        and all(i.get('ingredient_name_normalized') and _decimal_known(i.get('product_strength'))
                and i.get('product_strength_unit') for i in ingredients)
        and record.get('unit')
        and all(_decimal_known(record.get(k)) for k in ('dose_per_administration', 'administrations_per_day'))
    )


def process_guarded(previous, current, previous_internal, current_internal, family):
    batches = {'previous': previous, 'current': current}
    prepared = {side: _prepare_batch(results, family) for side, results in batches.items()}
    sources = []
    for side, internal in [('previous', previous_internal), ('current', current_internal)]:
        document = str(uuid4())
        counts = {'accepted_results': 0, 'review_results': 0}
        if len(internal) != len(batches[side]):
            raise ValueError('source/result count mismatch')
        for index, (raw, result) in enumerate(zip(internal, batches[side])):
            bucket = 'review_results' if result['status'] == 'FAILED' else 'accepted_results'
            row = raw.record.source_ref.get('row')
            sources.append({
                'ref': {'side': side, 'document_id': document, 'input_index': index},
                # B reports sheet names, not indexes. Do not guess an index or expose the name.
                'locator': {'sheet_index': None, 'row': row} if row is not None else None,
                'raw_fields': {k: v for k, v in raw.record.raw_row.items() if k in RAW_FIELDS},
                'normalization_ref': f'/{bucket}/{side}/{counts[bucket]}',
            })
            counts[bucket] += 1
    all_refs = [row['ref'] for row in sources]
    holds = []
    def hold(kind, message):
        holds.append({'kind': kind, 'message': message, 'affected_refs': deepcopy(all_refs)})
    if any(r['status'] == 'FAILED' or r.get('record') is None for rows in batches.values() for r in rows):
        hold('UNIDENTIFIED_FAILED_INPUT', '실패 후보가 있어 양쪽 자료 전체 비교를 실행하지 않았습니다.')
    records = {side: data['records'] for side, data in prepared.items()}
    if any(not _comparable(r) for rows in records.values() for r in rows):
        hold('UNKNOWN_COMPARISON_FIELDS', '성분·함량·단위 또는 비교 필수값이 미확인이라 전체 비교를 보류했습니다.')
    # Detect repeated identities within either entire side before greedy consumption.
    if any(_identity_rank(a, b) is not None for rows in records.values()
           for i, a in enumerate(rows) for b in rows[i + 1:]):
        hold('AMBIGUOUS_REPEATED_RECORDS', '반복 기록이 있어 전체 비교를 보류했습니다. 대표 기록을 자동 선택하지 않습니다.')
    # Same product with incompatible ingredient sets cannot mean same strength.
    if any(_identity_rank(a, b) is not None
           and sorted(i.get('ingredient_name_normalized') or '' for i in a.get('ingredients', []))
           != sorted(i.get('ingredient_name_normalized') or '' for i in b.get('ingredients', []))
           for a in records['previous'] for b in records['current']):
        if not any(h['kind'] == 'UNKNOWN_COMPARISON_FIELDS' for h in holds):
            hold('UNKNOWN_COMPARISON_FIELDS', '대응 제품의 성분 연결을 확인할 수 없어 전체 비교를 보류했습니다.')
    integrated = ({
        'accepted_results': {side: p['accepted_results'] for side, p in prepared.items()},
        'review_results': {side: p['review_results'] for side, p in prepared.items()},
        'reconciliation_result': None,
    } if holds else reconcile_normalization_results(previous, current, family))
    return {
        **integrated,
        'response_version': 'TASK_D_HIRA_V2', 'family_member_id': family,
        'processing': {'parser': 'DETERMINISTIC', 'file_processing': 'EXECUTED',
                       'official_data_mode': 'LOCAL_MOCK', 'persisted': False},
        'comparison': {'executed': not holds, 'holds': holds}, 'source_rows': sources,
        'current_intake_states': [] if holds else build_current_intake_states(integrated['reconciliation_result']),
    }
