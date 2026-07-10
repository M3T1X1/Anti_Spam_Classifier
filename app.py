from flask import Flask, render_template, request
import joblib

app = Flask(__name__)
model = joblib.load('model.pkl')

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        user_input = request.form.get("message")
        if user_input:
            prediction = model.predict([user_input])[0]
            result = str(prediction).lower()

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)