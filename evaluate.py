"""Evaluate field match exactness on labeled CSV with columns: pdf,question,expected.
Run: python evaluate.py gold.csv /path/to/pdf_folder
Sensitive insurance PDFs should remain local.
"""
import sys,csv,os
from app_pipeline import process_document
from qa_engine import ask

def run(csvpath,pdfdir):
    cache={};n=0;correct=0;missing=0
    with open(csvpath,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            pdf=row['pdf'];q=row['question'];expected=row['expected'].strip().casefold()
            if pdf not in cache:
                with open(os.path.join(pdfdir,pdf),'rb') as fh:cache[pdf]=process_document(fh.read())
            answer=ask(q,cache[pdf]); vals=[str(x['Value']).strip().casefold() for x in answer['answers']]
            passed=expected in vals if expected else not vals
            n+=1;correct+=passed;missing+=not vals
            print(('PASS' if passed else 'FAIL'),pdf,repr(q),'expected=',repr(expected),'got=',vals)
    print(f'Exact match accuracy: {correct}/{n} = {correct/n:.1%}' if n else 'No records')
    print('No-answer questions:',missing)
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: python evaluate.py gold.csv PDF_FOLDER')
    run(sys.argv[1],sys.argv[2])
