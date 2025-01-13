from datasets import load_dataset
import random


# Download QASPER dataset from HuggingFace https://huggingface.co/datasets/allenai/qasper
dataset = load_dataset("allenai/qasper")

# Split the dataset into train, validation, and test splits
train_dataset = dataset["train"]
validation_dataset = dataset["validation"]
test_dataset = dataset["test"]

random.seed(42)  # Set a random seed for reproducibility

# Randomly sample 800 rows from the training split
train_sampled_indices = random.sample(range(len(train_dataset)), 800)
train_samples = [train_dataset[i] for i in train_sampled_indices]

print(train_samples[0])

# Randomly sample 100 rows from the test split
test_sampled_indices = random.sample(range(len(test_dataset)), 80)
test_samples = [test_dataset[i] for i in test_sampled_indices]

# Now we have 800 research papers for training and 80 research papers to evaluate on