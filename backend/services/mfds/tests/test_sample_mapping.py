"""Synthetic analogues of supplied sample, not raw response or live requests."""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import pytest
import yaml

from backend.services.mfds.real_client import DEFAULT_CONFIG, RealMfdsClient, parse_item
from backend.services.mfds.sample_mapping import parse_material, parse_sample_xml

CFG = yaml.safe_load(DEFAULT_CONFIG.read_text())['sources']['drug']


def material(name='가상성분A', amount='500', total='1정615.04밀리그램', info=''):
    return f'총량 : {total}|성분명 : {name}|분량 : {amount}|단위 : 밀리그램|규격 : 가상규격|성분정보 : {info}'


def row(**updates):
    return {'ITEM_SEQ': '000001', 'ITEM_NAME': '가상제품500밀리그램',
            'MAIN_ITEM_INGR': '[SYNTHETIC-A]가상성분A', 'MATERIAL_NAME': material(),
            'EDI_CODE': '', 'TOTAL_CONTENT': '1615.04', 'PACK_UNIT': '10정/상자', **updates}


def test_direct_sample_fields_keep_total_and_ingredient_amount_separate():
    raw = row(); before = deepcopy(raw)
    component = parse_material(raw['MATERIAL_NAME'])[0]
    assert component.total == '1정615.04밀리그램'
    assert component.quantity == '500' and component.unit == '밀리그램'
    assert component.standard == '가상규격' and component.information == ''
    item = parse_item(raw, CFG)
    assert item.official_id == '000001' and item.name == raw['ITEM_NAME']
    assert item.insurance_code is None
    assert item.ingredients[0].amount == Decimal('500')
    assert item.ingredients[0].unit == '밀리그램'  # No unapproved conversion.
    assert item.ingredients[0].ingredient_id == 'SYNTHETIC-A'
    assert raw == before


def test_granule_quantity_and_equivalent_amount_are_not_interchanged():
    raw = row(MAIN_ITEM_INGR='[SYNTHETIC-G]가상성분과립', MATERIAL_NAME=material(
        '가상성분과립', '177.778', '1포304.000밀리그램', '가상성분(으)로서 160 밀리그램'))
    c = parse_material(raw['MATERIAL_NAME'])[0]
    assert c.quantity == '177.778' and c.information.endswith('160 밀리그램')
    assert c.total == '1포304.000밀리그램' and c.direct_amount() is None
    i = parse_item(raw, CFG).ingredients[0]
    assert i.name == '가상성분과립' and i.amount is None and i.unit is None


def test_compound_material_order_is_joined_by_name_not_position():
    raw = row(MAIN_ITEM_INGR='[SYNTHETIC-B]가상성분B|[SYNTHETIC-A]가상성분A',
              MATERIAL_NAME=material('가상성분A', '325.00')+';'+material('가상성분B','30.00'))
    ingredients = parse_item(raw, CFG).ingredients
    assert [(i.name, i.amount) for i in ingredients] == [
        ('가상성분B', Decimal('30.00')), ('가상성분A', Decimal('325.00'))]


@pytest.mark.parametrize('text', [
    '', material().replace('분량 : 500', '분량 : 읽기불가'),
    material().replace('성분명 : 가상성분A', '성분명 : 다른성분'),
    material()+';'+material(), material()+'|분량 : 900',
    material(total='총중량615.04밀리그램'), material(info='가상성분으로서 400mg'),
    material().replace('단위 : 밀리그램', '단위 : mg'),
])
def test_unknown_malformed_ambiguous_material_never_guesses_strength(text):
    ingredient = parse_item(row(MATERIAL_NAME=text), CFG).ingredients[0]
    assert ingredient.amount is None and ingredient.unit is None


def test_missing_material_does_not_use_total_content_package_or_product_name():
    raw = row(); raw.pop('MATERIAL_NAME')
    assert parse_item(raw, CFG).ingredients[0].amount is None
    assert parse_item(row(EDI_CODE='  '), CFG).insurance_code is None


def xml(items=1, total=1):
    fields = row()
    # Construct valid synthetic XML; never repair the supplied attachment here.
    import xml.etree.ElementTree as ET
    root = ET.Element('response'); h = ET.SubElement(root,'header')
    ET.SubElement(h,'resultCode').text = '00'
    body = ET.SubElement(root,'body')
    for k,v in [('totalCount',total),('pageNo',1),('numOfRows',3)]:
        ET.SubElement(body,k).text = str(v)
    container = ET.SubElement(body,'items')
    for n in range(items):
        node = ET.SubElement(container,'item')
        for k,v in {**fields,'ITEM_SEQ':f'00000{n}'}.items():
            ET.SubElement(node,k).text = v
    return ET.tostring(root,encoding='unicode')


def test_strict_xml_and_incomplete_page_never_establish_unique_candidate(tmp_path):
    payload = parse_sample_xml(xml(3,7))
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text()); cfg['sources'].pop('health_food')
    path = tmp_path/'single.yaml';path.write_text(yaml.safe_dump(cfg))
    c = RealMfdsClient(api_key='SYNTHETIC-ONLY',config_path=path,retries=0,
                       transport=lambda *args: payload)
    with patch('urllib.request.urlopen', side_effect=AssertionError('external call forbidden')):
        assert c.search_by_name('가상제품') == []
        assert c.last_failed and c._cache == {} and c.calls == 1
        assert c.find_by_code('000001') == [] and c.calls == 1
    assert len(payload['body']['items']) == 3 and payload['body']['totalCount'] == '7'


def test_valid_xml_empty_edi_and_direct_mapping():
    payload = parse_sample_xml(xml())
    item = parse_item(payload['body']['items'][0], CFG)
    assert item.insurance_code is None and item.ingredients[0].amount == Decimal('500')


@pytest.mark.parametrize('text', [
    'This XML file does not appear to have any style information.\n'+xml(),
    xml().replace('가상제품500밀리그램', '가상회사 A & B'),
    '<response>', '<!DOCTYPE response [<!ENTITY x "unsafe">]>'+xml(),
    xml().replace('<ITEM_NAME>', '<ITEM_NAME><nested>'),
])
def test_damaged_or_unsupported_xml_rejected_without_repair_or_content_leak(text):
    with pytest.raises(ValueError, match='XML') as exc:
        parse_sample_xml(text)
    assert '가상회사' not in str(exc.value) and 'unsafe' not in str(exc.value)
