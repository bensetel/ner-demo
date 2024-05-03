import pandas as pd
import numpy as np

from flair.data import Sentence
from flair.nn import Classifier


from flair.datasets import CONLL_03
from flair.data import MultiCorpus
from flair.embeddings import WordEmbeddings
from flair.models import SequenceTagger
from flair.trainers import ModelTrainer
from flair.datasets import ColumnCorpus

import torch
import re
import random

from src.corpus_generation import load_corpus

def demo():
    # make a sentence
    sentence = Sentence('I love Reed Smith.')
    print('sentence is:', sentence)
    # load the NER tagger
    #tagger = Classifier.load('flair/ner-english-large')
    tagger = Classifier.load('/home/ben/custom-model/final-model.pt')
    
    # run NER over sentence
    tagger.predict(sentence)
    for label in sentence.get_labels():
        print(label)

    # print the sentence with all annotations
    print(sentence)

def util(tagger, s):
    sentence = Sentence(s)
    tagger.predict(sentence)
    for label in sentence.get_labels():
        print(label)
    print(sentence)
    
def train_custom():
    tagger = SequenceTagger.load('flair/ner-english-large')
    custom_corpus = load_corpus('/home/ben/ner-takehome/data/firm_corpus')
    #trainer = ModelTrainer(tagger, custom_corpus)
    
    base_corpus = CONLL_03(base_path='/home/ben/ner-takehome/data')
    multi_corpus = MultiCorpus([custom_corpus, base_corpus])
    trainer = ModelTrainer(tagger, multi_corpus) 
    
    print('training....')
    trainer.fine_tune('custom-model', learning_rate=0.01, mini_batch_size=32, max_epochs=10)
    return trainer
    
    # label_dict = corpus.make_label_dictionary(label_type='ner')
    # embeddings = WordEmbeddings('glove')

    # model = SequenceTagger(hidden_size=256, embeddings=embeddings, tag_dictionary=label_dict, tag_type='ner')

    # trainer = ModelTrainer(model, corpus)
    # print('training...')
    # trainer.train('example-sec', learning_rate=0.1, mini_batch_size=32, max_epochs=10)
    # return trainer

            
