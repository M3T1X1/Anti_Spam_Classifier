import joblib
import pandas as pd
import nltk
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
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

label_map = {'ham': 0, 'spam': 1, 'smishing': 2}
dataset['LABEL'] = dataset['LABEL'].map(label_map)

X = dataset["TEXT"]
y = dataset["LABEL"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)


pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=8000, stop_words='english', ngram_range=(1, 2))),
    ('clf', LogisticRegression(C=0.5, random_state=42, max_iter=1000)),
])

pipeline.fit(X_train, y_train)

scores = cross_val_score(pipeline, X_train, y_train, cv=5)
print(f"Average Cross-Validation Accuracy: {scores.mean():.4f}\n")

y_pred_train = pipeline.predict(X_train)
y_pred_test = pipeline.predict(X_test)

print("="*60)
print(" Train data result: ")
print("="*60)
print(f"Train Accuracy: {accuracy_score(y_train, y_pred_train):.4f}")
print(classification_report(y_train, y_pred_train, target_names=['ham', 'spam', 'smishing']))

print("="*60)
print(" Test data result: ")
print("="*60)
print("="*60)
print(f"Test Accuracy: {accuracy_score(y_test, y_pred_test):.4f}")
print(classification_report(y_test, y_pred_test, target_names=['ham', 'spam', 'smishing']))

joblib.dump(pipeline, "model.pkl")
print("\nModel saved successfully as 'model.pkl'!")