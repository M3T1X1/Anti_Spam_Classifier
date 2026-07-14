import pandas as pd
import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt_tab')
    nltk.download('punkt')

def augment_text_dataset(input_file_path, output_file_path, min_words=3):
    df = pd.read_csv(input_file_path)
    augmented_records = []

    print(f"Rozpoczynam augmentację. Początkowa liczba wierszy: {len(df)}")

    for idx, row in df.iterrows():
        text = str(row['TEXT'])
        label = row['LABEL']

        augmented_records.append({'TEXT': text, 'LABEL': label})

        sentences = sent_tokenize(text)

        if len(sentences) > 1:
            for sentence in sentences:
                clean_sentence = sentence.strip()

                if len(clean_sentence.split()) >= min_words:
                    augmented_records.append({'TEXT': clean_sentence, 'LABEL': label})

    df_augmented = pd.DataFrame(augmented_records)

    df_augmented.drop_duplicates(subset=['TEXT'], inplace=True)

    df_augmented = df_augmented.sample(frac=1, random_state=42).reset_index(drop=True)

    df_augmented.to_csv(output_file_path, index=False)
    print(f"Augmentacja zakończona! Nowa liczba wierszy: {len(df_augmented)}")
    print(f"Plik zapisano w: {output_file_path}")



if __name__ == "__main__":
    INPUT_DATA = "../dataset.csv"
    OUTPUT_DATA = "../dataset_augmented.csv"
    augment_text_dataset(INPUT_DATA, OUTPUT_DATA, min_words=3)