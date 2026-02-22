"""
Train TF-IDF + MultinomialNB model using train_dataset.csv.
Produces vectorizer.pkl and hate_speech_model.pkl in the same directory
"""

import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import re
import os

def clean_text(s):
    s = str(s).lower()
    s = re.sub(r'http\S+', '', s)
    s = re.sub(r'[^a-zA-Z ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def main():
    # Read from current directory
    df = pd.read_csv('train_dataset.csv')
    df['text_clean'] = df['text'].astype(str).apply(clean_text)
    X = df['text_clean'].values
    y = df['label'].values

    vect = TfidfVectorizer(ngram_range=(1,2), max_features=8000)
    Xv = vect.fit_transform(X)
    clf = MultinomialNB()
    clf.fit(Xv, y)

    # Save in current directory (backend/ml/)
    joblib.dump(vect, 'vectorizer.pkl')
    joblib.dump(clf, 'hate_speech_model.pkl')
    print('✓ Training complete. Saved vectorizer.pkl and hate_speech_model.pkl')

if __name__ == '__main__':
    main()