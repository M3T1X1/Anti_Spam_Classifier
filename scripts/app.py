import os
import time

os.environ["HF_HUB_OFFLINE"] = "1"

from pathlib import Path
from flask import Flask, render_template, request
from transformers import pipeline

CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent.parent
MODEL_DIR = str(BASE_DIR / 'distilbert_spam_model' )
app = Flask(__name__)

classifier = None


def get_classifier():
    global classifier
    if classifier is None:
        print(f"Local model loading from: {MODEL_DIR}...")

        start_time = time.time()
        try:
            classifier = pipeline(
                "text-classification",
                model=MODEL_DIR,
                tokenizer=MODEL_DIR,
                device=-1,  # CPU
                local_files_only=True
            )

            # Koniec stopera
            elapsed_time = time.time() - start_time
            print(f"Model loaded in: {elapsed_time:.4f} seconds.")

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\nModel failed after {elapsed_time:.4f} seconds.")
            print(f"Error message: {str(e)}\n")
            raise e

    return classifier


LABEL_MAP = {
    'LABEL_0': 'ham', 'LABEL_1': 'spam', 'LABEL_2': 'smishing',
    'ham': 'ham', 'spam': 'spam', 'smishing': 'smishing'
}

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        user_input = request.form.get("message")
        if user_input and user_input.strip():
            try:
                clf = get_classifier()
                predictions = clf(user_input.strip())

                print("User message: ", user_input)
                print(f"[DEBUG RAW PREDICTION] {predictions}")
                raw_label = predictions[0]['label']
                result = LABEL_MAP.get(raw_label, "unknown")
                print(f"[DEBUG MAPPED RESULT] {result}")
            except Exception as err:
                print(f"Error message: {str(err)}")
                result = f"Internal error"

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)