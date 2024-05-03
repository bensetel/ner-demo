
def load_corpus(data_dir: str):
    columns = {0: 'text', 1: 'pos', 2: 'ner'}
    custom_corpus = ColumnCorpus(data_dir,
                                 columns,
                                 train_file='train.txt',
                                 test_file='test.txt')
    return custom_corpus

    
def scraped_firm_list_to_corpus(fp: str, new_fp: str):
    new_file_contents = []
    with open(fp, 'r') as f:
        data = f.readlines()
    for line in data:
        firm = line.split('|')[1]
        if '[' in firm:
            start_idx = firm.index('[') + 1
            end_idx = firm.index(']')
            firm = firm[start_idx:end_idx]
        firm = re.sub('[^a-zA-Z -&]', '', firm) #strip most non letter characters; leave spaces in for name delimiter; leave '-' in for hyphenated namesxo
        firm = [x for x in firm.split(' ') if x != '']
        new_str = ''
        for name in firm:
            if new_str == '':
                new_str += f'{name} N B-ORG\n'
            elif name == '&':
                new_str += f'{name} NFP I-ORG\n'
            else:
                new_str += f'{name} N I-ORG\n'
        new_str += '\n'
        new_file_contents.append(new_str)
    with open(new_fp, 'w') as f:
        for line in new_file_contents:
            f.write(line)

def split_train_test(fp: str, test_pct: float = 0.2):
    with open(fp, 'r') as f:
        data = f.read()
    data = data.split('\n\n') #firms delimited by two newlines in row
    random.shuffle(data)
    train_cutoff_idx = int(len(data)*(1 - test_pct))
    train = data[:train_cutoff_idx]
    test = data[train_cutoff_idx:]
    
    root_dir = '/'.join(fp.split('/')[:-1])
    with open(f'{root_dir}/train.txt', 'w') as f:
        for line in train:
            f.write(line)
            f.write('\n\n')
    
    with open(f'{root_dir}/test.txt', 'w') as f:
        for line in test:
            f.write(line)
            f.write('\n\n')
    
            
