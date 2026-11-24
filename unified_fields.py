"""Unified common fields + every source-backed table field across all PDF pages.

Explicit cards use the highest-priority verified source. Dynamic cards preserve
all distinct real table cells, including repeated labels for multiple insured
persons and tiny boxes. No schedule-only page filter or 350-field limit.
"""
import re
from collections import OrderedDict
from field_catalog import ALIASES, COMMON_EXPLICIT_FIELDS
from field_resolver import resolve_one,records_for
from live_lookup import batch_table_answers
from policy_schedule_verified import apply_verified


def key(name):
    return ' '.join(re.findall(r'[a-z0-9]+',str(name).lower()))


def canonical(label):
    raw=key(label).replace(' ','')
    for name in COMMON_EXPLICIT_FIELDS:
        if raw in {key(x).replace(' ','') for x in [name]+ALIASES.get(name,[])}:
            return name
    for name,aliases in ALIASES.items():
        if raw in {key(x).replace(' ','') for x in [name]+aliases}:
            return name
    return str(label).strip()


def safe_record(r):
    label=' '.join(str(r.get('Field','')).split())
    value=' '.join(str(r.get('Value','')).split())
    if not label or not value or len(label)>100 or len(value)>12000:return False
    if not re.search('[a-zA-Z]',label):return False
    if key(label)==key(value):return False
    if value.lower() in {'na','n/a','nil','none','-','--'}:return False
    # Corrupt pairs such as name = dateofbirth or amount 4283100 , .
    if key(label) in {'name','insured name'} and key(value) in {'date of birth','dateofbirth','dob'}:return False
    if re.fullmatch(r'[\d ]+\s*,\s*\.',value):return False
    if re.search(r'\d{1,2}/\d{1,2}/\d*[A-Za-z]+\d*',value):return False
    if re.search(r'(?i)^(?:note|important notice|terms and conditions|limit.*as to use)$',label):return False
    return True


def make_resolved(r):
    return {'value':str(r['Value']),'page':r.get('Page'),
            'evidence':r.get('Evidence',''),'person':r.get('Person',''),
            'bbox':r.get('BBox'),'status':'review' if r.get('Review') else 'found'}


def unified_fields(data,raw_pdf=None,deep_search=False,max_dynamic=None):
    """Return explicit fields, exhaustive dynamic field names, and resolved cards.

    Distinct table values remain distinct even when label repeats; a contextual
    suffix identifies different people/pages/cells without losing records.
    """
    records=records_for(data)
    verified=data.get('verified_schedule_records',[])
    strict=bool(verified) and any(r.get('Field')=='Policy Start Date' for r in verified) and bool(data.get('vehicle_records'))
    explicit=list(COMMON_EXPLICIT_FIELDS)
    resolved={name:resolve_one(name,data,records) for name in explicit}
    if verified:
        resolved=apply_verified(resolved,verified,strict_schedule=strict)
    # The deep path is optional; default never rescans a table per field.
    if deep_search and raw_pdf is not None:
        missing=[name for name in explicit if resolved[name]['status']=='not_found']
        if missing:
            questions=[];alias_map={}
            for name in missing:
                for alias in [name]+ALIASES.get(name,[]):
                    if alias not in alias_map:alias_map[alias]=name;questions.append(alias)
            try:
                for alias,hit in batch_table_answers(raw_pdf,questions).items():
                    name=alias_map[alias]
                    if resolved[name]['status']=='not_found' and hit.get('Value'):
                        resolved[name]={'value':str(hit['Value']),'page':hit.get('Page'),
                            'evidence':hit.get('Evidence',''),'person':hit.get('Person',''),
                            'bbox':hit.get('BBox'),'status':'review'}
            except Exception:pass
        if verified:resolved=apply_verified(resolved,verified,strict_schedule=strict)
    # Geometry sources have priority. No page/type filter and no arbitrary limit.
    # Avoid text-linearization guesses on pages where native table cells exist.
    sources=[]
    geometry_pages={r.get('Page') for r in data.get('geometry_records',[])}
    strong_sections=('geometry_records','vehicle_records','verified_schedule_records')
    for section in strong_sections:
        for record in data.get(section,[]):
            if safe_record(record):sources.append((section,record))
    # Other modules provide useful records from non-tabular text and image-only
    # pages. Suppress their table-linearized junk on geometry-supported pages.
    for section in ('schedule_records','contact_records','priority_records',
                    'indexed_records','proposal_records','checkbox_records'):
        for record in data.get(section,[]):
            if section in {'indexed_records','schedule_records'} and record.get('Page') in geometry_pages:
                continue
            if safe_record(record):sources.append((section,record))
    seen_source=set();counts={};dynamic=[]
    common_keys={key(x) for x in explicit}
    # Exclude explicit aliases only if source label unambiguously means a common field.
    for section,record in sources:
        label=str(record['Field']).strip()
        val=' '.join(str(record['Value']).split())
        person=str(record.get('Person','')).strip()
        page=record.get('Page')
        logical=canonical(label)
        identity=(key(logical),key(val),key(person),str(page))
        if identity in seen_source:continue
        seen_source.add(identity)
        if key(logical) in common_keys:continue
        # Keep all different values of the same label. Labels stay unique for
        # Streamlit state and exports; don't collapse 1st/2nd insured persons.
        stem=label
        if person and key(person) not in key(label):
            stem=f'{stem} — {person}'
        unique=key(stem)
        if unique in counts:
            counts[unique]+=1
            display=f'{stem} [page {page} · {counts[unique]}]'
        else:
            counts[unique]=1
            display=stem
        # If a label that was used earlier is emitted with a different context,
        # append a page qualifier. The exact record remains source-linked.
        while display in resolved:
            counts[unique]+=1
            display=f'{stem} [page {page} · {counts[unique]}]'
        rec=dict(record)
        if section in {'indexed_records','proposal_records'} and rec.get('Method') not in {
                'verified person table','verified policy schedule','vehicle table geometry'}:
            rec['Review']=True
        resolved[display]=make_resolved(rec)
        dynamic.append(display)
    return explicit,dynamic,resolved
