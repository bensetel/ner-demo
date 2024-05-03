import os
if 'Users' in os.getcwd(): #todo - unkludge
    root_path = '/Users/ben/Desktop/job/ner-takehome'
else:
    root_path = '/home/ben/ner-takehome'
os.chdir(root_path)


import pandas as pd
import numpy as np
import re

from huggingface_hub import login
import transformers
import torch

from src.database import Neo4jDatabase
from src.csv_processing import process_article_text, load_csvs, process_df
from src.string_filters import is_name, has_bad_keyword, is_atl_writer

class LLamaPredictor():
    def __init__(self) -> None:
        self.db = Neo4jDatabase(URI = "neo4j://10.249.64.7", AUTH = ("neo4j", "[bigsecret]")
        self.pipeline = transformers.pipeline(
            "text-generation",
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            model_kwargs={"torch_dtype": torch.bfloat16},
            device_map="auto",
        )

    def make_prediction(self, input_article: str) -> str:
        messages = [
            {"role": "system", "content": """You are an expert system that generates knowledge graphs from news articles about law firms. You output the names of employees and the firms they work for mentioned in the article. Please generate a list of all law firms and employees specifically mentioned in the article. It is okay if no firms or employees are mentioned! Please format your output as:
    "- Firm Name
            + Employee name"""},
            {"role": "user", "content": f"Please analyze generate a knowledge graph for the following text: {input_article}"},
        ]

        prompt = self.pipeline.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
        )

        terminators = [
            self.pipeline.tokenizer.eos_token_id,
            self.pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        outputs = self.pipeline(
            prompt,
            max_new_tokens=256,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        return(outputs[0]["generated_text"][len(prompt):])


    def update_db(self, prediction: str, url: str, title: str) -> None:
        if '*' in prediction: #sometimes model uses * instead of - to denote a firm, despite instruction
            prediction = re.sub('\*', '-', prediction)
        full_text = [x.strip() for x in prediction.split('-') if x.strip() != ''][1:]

        for chunk in full_text:
            firm_and_ees = [x.strip() for x in chunk.split('+') if x.strip() != '']
            if len(firm_and_ees) == 0:
                continue

            firm_name = firm_and_ees[0]
            if "-" in firm_name:
                firm_name = re.sub('-', '', firm_name).strip()
            if ":" in firm_name:
                firm_name = re.sub(':', '', firm_name).strip()
            if has_bad_keyword(firm_name):
                    continue

            self.db.add_firm_mention(firm_name, url, title)

            if len(firm_and_ees) > 1: #if we have employees
                for employee in firm_and_ees[1:]:
                    if "+" in employee:
                        employee = re.sub("+", "", employee)
                    if '(' in employee:
                        employee = re.sub('\(.*', '', employee).strip()
                    employee = employee.strip()
                    if has_bad_keyword(employee) or not(is_name(employee)):
                        continue
                    #print('adding employee-firm relationship:', firm_name, employee)
                    self.db.add_employee(firm_name, employee)
                    self.db.add_employee_mention(employee, url, title)


    def make_predictions(self) -> None:
        login('[big_secret]')
        df = load_csvs(f'{root_path}/data/article_storage')
        df = process_df(df)
        for text, url, title in zip(df['text'].values, df['url'].values, df['title'].values):
            prediction = self.make_prediction(text)
            print('#'*80)
            print('prediction is:', prediction)
            self.update_db(prediction, url, title)


if __name__ == "__main__":
    model = LLamaPredictor()
    model.make_predictions()
