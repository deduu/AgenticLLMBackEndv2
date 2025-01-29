from datasets import load_dataset
 
# Dataset id from huggingface.co/dataset
dataset_id = "DevQuasar/llm_router_dataset-synth"
# dataset_id = "legacy-datasets/banking77"
 
# Load raw dataset
raw_dataset = load_dataset(dataset_id)
 
print(f"Train dataset size: {len(raw_dataset['train'])}")
print(f"Test dataset size: {len(raw_dataset['test'])}")

from transformers import AutoTokenizer
 
# Model id to load the tokenizer
# model_id = "answerdotai/ModernBERT-base"
model_id = "google-bert/bert-base-uncased"
# Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.model_max_length = 512 # set model_max_length to 512 as prompts are not longer than 1024 tokens
 
# Tokenize helper function
def tokenize(batch):
    return tokenizer(batch['prompt'], padding='max_length', truncation=True, return_tensors="pt")
 
# Tokenize dataset
raw_dataset =  raw_dataset.rename_column("label", "labels") # to match Trainer
tokenized_dataset = raw_dataset.map(tokenize, batched=True,remove_columns=["prompt"])
 
print(tokenized_dataset["train"].features.keys())
# dict_keys(['input_ids', 'token_type_ids', 'attention_mask','lable'])

from transformers import AutoModelForSequenceClassification

 
# Prepare model labels - useful for inference
labels = tokenized_dataset["train"].features["labels"].names
num_labels = len(labels)
label2id, id2label = dict(), dict()
for i, label in enumerate(labels):
    label2id[label] = str(i)
    id2label[str(i)] = label
 
# Download the model from huggingface.co/models
model = AutoModelForSequenceClassification.from_pretrained(
    model_id, num_labels=num_labels, label2id=label2id, id2label=id2label,
)

import numpy as np
from sklearn.metrics import f1_score
 
# Metric helper method
def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    score = f1_score(
            labels, predictions, labels=labels, pos_label=1, average="weighted"
        )
    return {"f1": float(score) if score == 1 else score}

from huggingface_hub import HfFolder
from transformers import Trainer, TrainingArguments
 
# Define training args
training_args = TrainingArguments(
    output_dir= "init_modernbert-llm-router",
    per_device_train_batch_size=32,
    per_device_eval_batch_size=16,
    learning_rate=5e-5,
		num_train_epochs=5,
    bf16=True, # bfloat16 training 
    optim="adamw_torch_fused", # improved optimizer 
    # logging & evaluation strategies
    logging_strategy="steps",
    logging_steps=100,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    # push to hub parameters
    report_to="tensorboard",
    push_to_hub=True,
    hub_strategy="every_save",
    hub_token=HfFolder.get_token(),
 
)
 
# Create a Trainer instance
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    compute_metrics=compute_metrics,
)

# Start training
trainer.train()


# Save processor and create model card
tokenizer.save_pretrained("init_modernbert-llm-router")
trainer.create_model_card()
trainer.push_to_hub()

from transformers import pipeline
 
# load model from huggingface.co/models using our repository id
classifier = pipeline("sentiment-analysis", model="init_modernbert-llm-router", device=0)
 
sample = "How does the structure and function of plasmodesmata affect cell-to-cell communication and signaling in plant tissues, particularly in response to environmental stresses?"
 
 
pred = classifier(sample)
print(pred)
# [{'label': 'large_llm', 'score': 1.0}]