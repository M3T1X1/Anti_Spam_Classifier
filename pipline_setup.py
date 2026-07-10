import joblib
import pandas as pd
import nltk
from pandas.io.common import file_exists
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

def ensure_nltk_resource(resource_name, download_name):
    try:
        nltk.data.find(f'{resource_name}/{download_name}')
    except LookupError:
        nltk.download(download_name)

ensure_nltk_resource('tokenizers', 'punkt_tab')
ensure_nltk_resource('corpora', 'stopwords')
ensure_nltk_resource('corpora', 'wordnet')

dataset = pd.read_csv("dataset.csv")

X = dataset["TEXT"]
y = dataset["LABEL"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=10000, stop_words='english')),
    ('clf', MultinomialNB())
])

pipeline.fit(X_train, y_train)

scores = cross_val_score(pipeline, X_train, y_train, cv=5)
print(f"Average Cross-Validation Accuracy: {scores.mean():.4f}")

y_pred = pipeline.predict(X_test)
print(f"Test Set Accuracy: {accuracy_score(y_test, y_pred)}")
print(classification_report(y_test, y_pred))

if not file_exists('model.pkl'):
    joblib.dump(pipeline, "model.pkl")
    print(f"Model saved!")
else:
    pass
