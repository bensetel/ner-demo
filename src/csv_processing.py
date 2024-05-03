import pandas as pd
import os
import re
import glob
import ast

def load_csvs(path: str) -> pd.DataFrame:
    all_frames = []
    all_files = glob.glob(os.path.join(path , "*.csv"))
    for csv in all_files:
        df = pd.read_csv(csv)
        all_frames.append(df)
    df = pd.concat(all_frames)
    return df

def process_article_text(input_text: str) -> str:
    if type(input_text) != type(''):
        return 'NO TEXT'
     
    start_pattern = r'(javascript:void("#ea-share-count-email"))'
    end_pattern = '\n####Topics\n'
    if not(start_pattern in input_text) or not(end_pattern in input_text):
        return 'NO TEXT'
    start_idx = input_text.index(start_pattern)
    end_idx = input_text.index(end_pattern)
    input_text = input_text[start_idx+len(start_pattern):end_idx]
    if 'Earlier:' in input_text:
        input_text = input_text[:input_text.index('Earlier:')]
    input_text = re.sub('Sponsored.*\n', '', input_text)
    input_text = re.sub('\(https.*\)', '', input_text)
    input_text = re.sub('\[|\]', '', input_text)
    return input_text.strip()


def process_meta(row: str) -> dict:
    try:
        row = ast.literal_eval(row)
    except Exception:
        row = {}
    return row


def process_df(df: pd.DataFrame) -> pd.DataFrame:
    df['meta'] = df['meta'].apply(process_meta)
    df = df[df['meta'] != {}]
    df['url'] = df['meta'].apply(lambda x: x['url'])
    df['title'] = df['meta'].apply(lambda x: x['meta']['title'])
    df['text'] = df['text'].apply(process_article_text)
    df = df[df['text'] != 'NO TEXT']
    return df
