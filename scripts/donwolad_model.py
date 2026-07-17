import gdown
import zipfile
import os
import sys


def setup_model():
    FILE_ID = '16q6_CvLRsdG1idW6MnnGuf044-D0cnms'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    model_folder = os.path.join(base_dir, 'distilbert_spam_model')
    model_zip = os.path.join(base_dir, 'model.zip')
    model_config_path = os.path.join(model_folder, 'config.json')

    if os.path.exists(model_folder) and os.path.exists(model_config_path):
        print(f"Model and config found in {model_folder}. Skipping download.")
        return

    print(f"Downloading model from Google Drive (ID: {FILE_ID})...")
    try:
        gdown.download(id=FILE_ID, output=model_zip, quiet=False)
    except Exception as e:
        print(f"Error during download: {e}")
        return

    if os.path.exists(model_zip):
        print("Unzipping model...")
        try:
            os.makedirs(model_folder, exist_ok=True)
            with zipfile.ZipFile(model_zip, 'r') as zip_ref:
                zip_ref.extractall(model_folder)

            os.remove(model_zip)
            print(f"Model successfully installed in: {model_folder}")
        except Exception as e:
            print(f"Error during extraction: {e}")
    else:
        print("Error: The model file was not downloaded.")

if __name__ == "__main__":
    setup_model()