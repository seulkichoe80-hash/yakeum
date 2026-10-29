"""Conservative offline support for the supplied sample, not a full MFDS spec."""
from dataclasses import dataclass
from decimal import Decimal
import re
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class MaterialComponent:
    total: str
    name: str
    quantity: str
    unit: str
    standard: str
    information: str

    def direct_amount(self):
        # Only the observed single-tablet basis, with no conversion statement.
        # Granules/extracts/equivalents require a separately agreed mapping.
        if (self.information or '과립' in self.name
                or not re.fullmatch(r'1정\d+(?:\.\d+)?밀리그램', self.total)
                or self.unit != '밀리그램'
                or not re.fullmatch(r'\d+(?:\.\d+)?', self.quantity)):
            return None
        return Decimal(self.quantity)


def parse_material(text):
    """Retain total, ingredient quantity and conversion text separately.

    Unknown/duplicate/incomplete fields invalidate this optional supplement.
    Never consume TOTAL_CONTENT, PACK_UNIT or product-name digits.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    fields = {'총량', '성분명', '분량', '단위', '규격', '성분정보'}
    components = []
    for part in text.split(';'):
        values = {}
        for token in part.strip().split('|'):
            key, sep, value = token.partition(':')
            key = key.strip()
            if not sep or key not in fields or key in values:
                return []
            values[key] = value.strip()
        if set(values) != fields or not values['성분명']:
            return []
        components.append(MaterialComponent(*(values[k] for k in
            ('총량', '성분명', '분량', '단위', '규격', '성분정보'))))
    return components


def parse_sample_xml(text):
    """Strict offline XML -> existing client's envelope; no copy repair.

    Reject declarations/entities, nested field values and duplicate fields.
    Errors contain no response contents. Does not authorize a live request.
    """
    if not isinstance(text, str) or len(text.encode('utf-8')) > 2_000_000:
        raise ValueError('XML input type or size is invalid')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
        raise ValueError('XML declarations are not supported')
    try:
        root = ET.fromstring(text)
        if root.tag != 'response':
            raise ValueError()
        header, body = root.find('header'), root.find('body')
        if header is None or body is None or body.find('items') is None:
            raise ValueError()
        def flat(node, fields):
            result = {}
            for key in fields:
                nodes = node.findall(key)
                if len(nodes) > 1 or (nodes and len(nodes[0])):
                    raise ValueError()
                if nodes:
                    result[key] = (nodes[0].text or '').strip()
            return result
        fields = ('ITEM_SEQ', 'ITEM_NAME', 'MATERIAL_NAME', 'MAIN_ITEM_INGR', 'EDI_CODE')
        return {'header': flat(header, ('resultCode', 'resultMsg')),
                'body': {**flat(body, ('totalCount', 'pageNo', 'numOfRows')),
                         'items': [flat(row, fields) for row in body.find('items').findall('item')]}}
    except (ET.ParseError, ValueError, AttributeError):
        raise ValueError('XML is malformed or has an unsupported structure') from None
