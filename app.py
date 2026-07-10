import streamlit as st
import joblib

model = joblib.load('model.pkl')

st.title("Spam Detection App")
st.write("Enter a message below to check if it's spam, ham, or smishing.")

user_input = st.text_area("Message:", placeholder="Type your message here...")

if st.button("Check for Spam"):
    if user_input:
        prediction = model.predict([user_input])[0]

        label_map = {0: 'Ham', 1: 'Spam', 2: 'Smishing'}
        result = str(prediction).lower()

        if prediction == "ham":
            st.success(f"Result: {result.capitalize()}")
        elif prediction == "spam":
            st.error(f"Result: {result.capitalize()}")
        elif prediction == "smishing":
            st.warning(f"Result: {result.capitalize()}")
        else:
            st.error(f"Result: {result}")
    else:
        st.warning("Please enter some text first.")
