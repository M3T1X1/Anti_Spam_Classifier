import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
from transformers import Trainer, TrainingArguments
from datasets import Dataset as HFDataset
from sklearn.metrics import confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
from transformers import DataCollatorWithPadding

dataset = pd.read_csv("../dataset_augmented.csv")

label_map = {'ham': 0, 'spam': 1, 'smishing': 2}
dataset['LABEL'] = dataset['LABEL'].map(label_map)

df = pd.DataFrame({
    'text': dataset["TEXT"].astype(str),
    'label': dataset["LABEL"]
})

train_df, test_df = train_test_split(df, test_size=0.1, random_state=42, stratify=df['label'])

train_dataset = HFDataset.from_pandas(train_df.reset_index(drop=True))
test_dataset = HFDataset.from_pandas(test_df.reset_index(drop=True))

MODEL_NAME = "distilbert-base-uncased"
tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)

def tokenize_function(examples):
    return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=128)

train_dataset = train_dataset.map(tokenize_function, batched=True)
test_dataset = test_dataset.map(tokenize_function, batched=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device.upper()}")

id2label = {0: "ham", 1: "spam", 2: "smishing"}
label2id = {"ham": 0, "spam": 1, "smishing": 2}

model = DistilBertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label=id2label,
    label2id=label2id
)
model.to(device)

def tokenize_function(examples):
    return tokenizer(examples['text'], truncation=True)

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, predictions)
    return {"accuracy": acc}

training_args = TrainingArguments(
    output_dir="../results",
    num_train_epochs=3,
    per_device_train_batch_size=64,
    per_device_eval_batch_size=64,
    fp16=True,
    dataloader_num_workers=2,
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=3e-5,
    weight_decay=0.1,
    warmup_ratio=0.1,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    logging_steps=10,
    disable_tqdm=False
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics,
    data_collator=data_collator
)

print("Training...")
trainer.train()

print("\n" + "="*60)
print(" Generating reports ")
print("="*60)

test_predictions = trainer.predict(test_dataset)
y_pred_test = np.argmax(test_predictions.predictions, axis=-1)
y_test = test_df['label'].values

print(f"Test Accuracy: {accuracy_score(y_test, y_pred_test):.4f}")
print(classification_report(y_test, y_pred_test, target_names=['ham', 'spam', 'smishing']))

OUTPUT_DIR = "../distilbert_spam_model"
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\nModel and Tokenizer saved at: '{OUTPUT_DIR}'!")

cm = confusion_matrix(y_test, y_pred_test)
sns.heatmap(cm, annot=True, fmt='d', xticklabels=label_map.keys(), yticklabels=label_map.keys())
plt.show()