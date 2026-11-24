"""Reusable pipeline independent of Streamlit for tests/batch evaluation."""
from ocr_runtime import configure_tesseract
from extractor import extract
from checkbox_fields import checkbox_records
from document_index import extract_index
from priority_fields import extract_priority_fields
from geometry_contacts import extract_contact_geometry
from schedule_geometry import schedule_records
from table_cache import table_session
from vehicle_geometry import vehicle_records
from policy_schedule_verified import policy_schedule_records
from comprehensive_tables import extract_every_table
from geometry_all_pages import extract_geometry_all_pages

def process_document(data,ocr_engine='auto'):
    configure_tesseract()
    with table_session():
        r=extract(data)
        idx=extract_index(data,ocr_engine)
        r.update({'pages':idx['text_pages'],'modes':idx['modes'],'page_count':len(idx['pages']),
                  'indexed_records':idx['records'],'dynamic_records':idx['records'],'index_pages':idx['pages']})
        r['checkbox_records']=checkbox_records(data,r.get('proposal_records',[]))
        r['priority_records']=extract_priority_fields(data,idx['text_pages'])
        r['contact_records']=extract_contact_geometry(data)
        r['schedule_records']=schedule_records(data)
        r['vehicle_records']=list(vehicle_records(data))
        r['verified_schedule_records']=policy_schedule_records(data)
        r['comprehensive_table_records']=extract_every_table(data)
        r['geometry_records'],r['unpaired_cells']=extract_geometry_all_pages(data)
    return r
