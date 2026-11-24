"""Optional LayoutLMv3 token classification fine-tune on labeled REAL annotations.

JSONL per page:
{"image":"/path/page.png","words":["PAN", "QWERT6789P"],
 "boxes":[[10,20,100,40],[120,20,230,40]],"labels":["B-KEY","B-VALUE"]}
Boxes are integers normalized to [0,1000]. Split data by DOCUMENT, not page,
into train.jsonl and valid.jsonl to prevent data leakage.

Run: python train_layoutlmv3.py train.jsonl valid.jsonl ./layoutlm_model
Requires requirements-layoutlm.txt and suitable memory/GPU.
"""
import sys,json
from PIL import Image

def read_jsonl(path):
    with open(path,encoding='utf-8') as f:
        rows=[json.loads(x) for x in f if x.strip()]
    for r in rows:
        if not(len(r['words'])==len(r['boxes'])==len(r['labels'])):raise ValueError('word/box/label count mismatch')
        if any(len(box)!=4 or any(not isinstance(v,int) or v<0 or v>1000 for v in box) for box in r['boxes']):raise ValueError('Box must be normalized integer x0,y0,x1,y1 in 0..1000')
    return rows

class Pages:
    def __init__(self,rows,processor,vocab):self.rows=rows;self.processor=processor;self.vocab=vocab
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i]
        enc=self.processor(Image.open(r['image']).convert('RGB'),r['words'],boxes=r['boxes'],
                           word_labels=[self.vocab[v] for v in r['labels']],padding='max_length',truncation=True,return_tensors='pt')
        return {k:v.squeeze(0) for k,v in enc.items()}

def train(trainfile,validfile,outdir):
    from transformers import AutoProcessor,LayoutLMv3ForTokenClassification,Trainer,TrainingArguments
    trainrows=read_jsonl(trainfile);validrows=read_jsonl(validfile)
    if not trainrows or not validrows:raise ValueError('Train and validation annotations required')
    labels=sorted(set(v for x in trainrows+validrows for v in x['labels']))
    if 'O' not in labels:labels.insert(0,'O')
    vocab={lab:i for i,lab in enumerate(labels)}
    processor=AutoProcessor.from_pretrained('microsoft/layoutlmv3-base',apply_ocr=False)
    model=LayoutLMv3ForTokenClassification.from_pretrained('microsoft/layoutlmv3-base',num_labels=len(labels),
                      id2label={v:k for k,v in vocab.items()},label2id=vocab)
    training=TrainingArguments(output_dir=outdir,learning_rate=3e-5,per_device_train_batch_size=1,
                               per_device_eval_batch_size=1,num_train_epochs=4,save_strategy='epoch',
                               eval_strategy='epoch',logging_steps=10,load_best_model_at_end=True,report_to='none')
    trainer=Trainer(model=model,args=training,train_dataset=Pages(trainrows,processor,vocab),eval_dataset=Pages(validrows,processor,vocab))
    trainer.train(); trainer.save_model(outdir);processor.save_pretrained(outdir)
    print('Saved trained checkpoint:',outdir)
    print('Next: evaluate field-level F1 on separate unseen documents; this alone does not guarantee QA accuracy.')

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('python train_layoutlmv3.py train.jsonl valid.jsonl output_dir')
    train(*sys.argv[1:])
