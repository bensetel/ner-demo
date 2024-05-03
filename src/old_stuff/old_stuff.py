
def bertify():    
    tokenizer = BertTokenizer.from_pretrained('pile-of-law/legalbert-large-1.7M-2')
    model = BertModel.from_pretrained('pile-of-law/legalbert-large-1.7M-2')
    text = "I hate Davis Polk"
    encoded_input = tokenizer(text, return_tensors='pt')
    output = model(**encoded_input)
    return output
#mps_device = torch.device("mps")
#flair.device = 'mps:0'

#from transformers import BertTokenizer, BertModel
#from transformers import AutoModelForTokenClassification

