import os
if 'Users' in os.getcwd(): #todo - unkludge
    root_path = '/Users/ben/Desktop/job/ner-takehome'
else:
    root_path = '/home/ben/ner-takehome'
os.chdir(root_path)


import re
import pandas as pd

from flair.data import Sentence
from flair.models import SequenceTagger
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


from src.database import Neo4jDatabase
from src.string_filters import is_name, has_bad_keyword, is_atl_writer, remove_word
from src.csv_processing import process_article_text, load_csvs, process_df


class BabelFlairPredictor():
    def __init__(self) -> None:
        self.db = Neo4jDatabase(URI = "neo4j://10.249.64.11", AUTH = ("neo4j", "[big_secret]"))
        self.relation_tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")
        self.relation_model= AutoModelForSeq2SeqLM.from_pretrained("Babelscape/rebel-large")
        self.relation_args = {
            "max_length": 256,
            "length_penalty": 0,
            "num_beams": 10,
            "num_return_sequences": 1,
        }
        self.entity_tagger = SequenceTagger.load('flair/ner-english-large')
        self.known_firms = self.db.return_known_firm_names()
        self.known_halluciations = [
            {'head': 'John F. Kennedy School of Government', 'type': 'part of', 'tail': 'Harvard University'},
            {'head': 'Wall Street Crash of 1929', 'type': 'point in time', 'tail': '1929'}
        ]
        self.ENTITY_CONFIDENCE_THRESHOLD = 0.9

    @staticmethod
    def extract_triplets(text: str) -> list[dict]:
        triplets = []
        relation, subject, relation, object_ = '', '', '', ''
        text = text.strip()
        current = 'x'
        for token in text.replace("<s>", "").replace("<pad>", "").replace("</s>", "").split():
            if token == "<triplet>":
                current = 't'
                if relation != '':
                    triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
                    relation = ''
                subject = ''
            elif token == "<subj>":
                current = 's'
                if relation != '':
                    triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
                object_ = ''
            elif token == "<obj>":
                current = 'o'
                relation = ''
            else:
                if current == 't':
                    subject += ' ' + token
                elif current == 's':
                    object_ += ' ' + token
                elif current == 'o':
                    relation += ' ' + token
        if subject != '' and relation != '' and object_ != '':
            triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
        return triplets

    def predict_relations(self, sentence: str) -> list[dict]:
        model_inputs = self.relation_tokenizer(sentence, max_length=256, padding=True, truncation=True, return_tensors = 'pt')
        generated_tokens = self.relation_model.generate(
            model_inputs["input_ids"].to(self.relation_model.device),
            attention_mask=model_inputs["attention_mask"].to(self.relation_model.device),
            **self.relation_args,
        )
        all_preds = self.relation_tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)
        relations = []
        for pred in all_preds:
            result = self.extract_triplets(pred)
            if result != []:
                relations.append(result[0])
        return relations

    def analyze_article(self, input_text: str, url: str, title: str) -> None:
        tag_text = []
        already_seen = []
        firms_mentioned = []
        people_mentioned = []

        ###Use Flair's ner-large model to tag entities
        sentence = Sentence(input_text)
        self.entity_tagger.predict(sentence)
        article_text = sentence.text.strip()
        tagged_entities = sentence.to_dict()['entities']
        names_and_labels = [(x['text'],  x['labels'][0]['value']) for x in tagged_entities]
        print('-'*80)
        print('names and labels are:\n', names_and_labels)
        for entity in tagged_entities:
            confidence = entity['labels'][0]['confidence']
            name = entity['text']
            label = entity['labels'][0]['value']
            if (label != 'ORG') and (label != 'PER'):
                continue
            if name in already_seen: #model tags each *occurence* of an entity in the text, but we only care whether it's there at all or not -> only need to deal w/ each entity once
                continue
            if (confidence < self.ENTITY_CONFIDENCE_THRESHOLD) or has_bad_keyword(name) or ((label != 'ORG') and (label != 'PER')) or ((label == 'PER') and not(is_name(name))) or (len(name) < 3):
                article_text = remove_word(name, article_text)
            else:
                tag_text.append((name, f'{name}/{label}/{confidence}'))
                if (label == 'ORG') and (name[0].isupper()):
                    self.db.add_firm_mention(name, url, title)
                    firms_mentioned.append(name) #internal list for babel only
                elif label == 'PER':
                    people_mentioned.append(name) #internal list for babel only; we only add to database if babel determines they are related to a firm, below
            already_seen.append(name)

        ### Use Babel's rebel model to extract relations among tagged entities
        num_detected_entities = len(tag_text)
        if num_detected_entities < 2:
            return
        if len(article_text) < 50:
            return
        input_sentence = article_text + ' |  ' + f"[{'; '.join([x[1] for x in tag_text])}]"
        self.relation_args = {'max_length': 256, 'length_penalty': 0, 'num_beams': 5*num_detected_entities, 'num_return_sequences': num_detected_entities//2}  #update number of relations we want to predict based on how many entities we tagged
        predicted_relations = self.predict_relations(input_sentence)
        for relation in predicted_relations:
            if relation in self.known_halluciations: #if we've started hallucinating, the rest will be garbage too
                break
            head = relation['head']
            tail = relation['tail']
            if has_bad_keyword(head) or has_bad_keyword(tail):
                continue
            if (head in firms_mentioned) and (tail in people_mentioned):
                self.db.add_employee(head, tail)
                self.db.add_employee_mention(tail, url, title)
            elif (tail in firms_mentioned) and (head in people_mentioned):
                self.db.add_employee(tail, head)
                self.db.add_employee_mention(head, url, title)

    def make_predictions(self) -> None:
        df = load_csvs(f'{root_path}/data/article_storage')
        df = process_df(df)
        for text, url, title in zip(df['text'].values, df['url'].values, df['title'].values):
            self.analyze_article(text, url, title)

if __name__ == "__main__":
    model = BabelFlairPredictor()
    model.make_predictions()
