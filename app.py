from flask import Flask, render_template, request
import joblib

app = Flask(__name__)

model = joblib.load('model.pkl')

LABEL_MAP = {0: 'ham', 1: 'spam', 2: 'smishing'}

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        user_input = request.form.get("message")
        if user_input:
            prediction = model.predict([user_input])[0]
            result = LABEL_MAP.get(prediction, "unknown")
            print(f"[DEBUG] Tekst: {user_input} -> Klasa: {prediction} ({result})")

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)