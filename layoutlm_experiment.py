"""OPTIONAL research check: LayoutLMv3-base forward pass only; NOT field extraction.
No training happens here; a trained token classification head and labeled data are required.
"""
def run_demo():
    from transformers import AutoProcessor,LayoutLMv3Model
    from PIL import Image
    import torch
    processor=AutoProcessor.from_pretrained('microsoft/layoutlmv3-base',apply_ocr=True)
    model=LayoutLMv3Model.from_pretrained('microsoft/layoutlmv3-base')
    img=Image.new('RGB',(600,800),'white')
    encoded=processor(img,return_tensors='pt',truncation=True,padding='max_length')
    with torch.no_grad():result=model(**encoded)
    print('Base model inference output shape:',result.last_hidden_state.shape)
    print('This is NOT extracted fields. Train a token classifier to output labels.')
if __name__=='__main__':run_demo()
