import csv
from datasets import  load_dataset
import evaluate
from pathlib import Path

list_replacements = [
  (" .", "."), 
  (" ,", ","),
  (" '", "'"),
  (" ?", "?"),
  (" !", "!"),
  (" :", ":"),
  (" ;", ";"),
  (" n't", "n't"),
  (" v", "v"),
  ("2 0 0 6", "2006"),
  ("5 5", "55"),
  ("4 0 0", "400"),
  ("1 7-5 0", "1750"),
  ("2 0 %", "20%"),
  ("5 0", "50"),
  ("1 2", "12"),
  ("1 0", "10"),
  ('" ballast water', '"ballast water')
  ]

def correct_spacing(item):
    """ we iterate through the list of all replacements per each item in dataset"""
    for fix in list_replacements:
        item = item.replace(fix[0], fix[1])
    return item

def generate_csv(csv_path, dataset):
    """ apply spacing corrections and save out matched pairs to csv file as dataset"""
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["input", "target"])
        for case in dataset:
     	    # Adding the t5 task indication prefix to input 
            input_text = case["sentence"]
            input_text = correct_spacing(input_text)

            for correction in case["corrections"]:
              correction = correct_spacing(correction)
              # a few of the cases contain blank strings. 
              if input_text and correction:
                writer.writerow([input_text, correction])

train_dataset = load_dataset("jfleg", split='validation[:]') 
eval_dataset = load_dataset("jfleg", split='test[:]')

jfleg_dir = Path.cwd()/'jfleg_dataset'  # if you only use 'jfleg', hf will try and use that and complain
jfleg_dir.mkdir(parents=True,exist_ok=True)
c4_dir = Path.cwd()/'c4_dataset'
c4_dir.mkdir(parents=True,exist_ok=True)

j_train_file = jfleg_dir/'jtrain.csv'
j_eval_file = jfleg_dir/'jeval.csv'
generate_csv(j_train_file, train_dataset)
generate_csv(j_eval_file, eval_dataset)

c4_dataset = load_dataset("liweili/c4_200m", streaming = True, trust_remote_code=True)
iterator = iter(c4_dataset['train'])
import csv

def c4_generate_csv(csv_path, iterator, num_examples):
    with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["input", "target"])
        
        for i in range(num_examples):
            try:
                data = next(iterator)  # Handle StopIteration safely
            except StopIteration:
                print("Reached end of iterator before expected count.")
                break
            
            input_text = correct_spacing(data["input"])
            correction = correct_spacing(data["output"])
            
            if input_text and correction:  # Ensure non-empty values
                writer.writerow([input_text, correction])


c4_dir = Path.cwd()/'c4_dataset'
c4_dir.mkdir(parents=True,exist_ok=True)

c4_filename = c4_dir/'c4train_10k.csv'
c4_generate_csv(c4_filename, iterator, num_examples=10000)
merge_list = [j_train_file, c4_filename, ]
import pandas as pd
combined_csv = pd.concat([pd.read_csv(fn) for fn in merge_list])
merged_name = "gtrain_10k.csv"
combined_csv.to_csv(merged_name, index=False, encoding = 'utf-8-sig', )
eval_name = "grammar_validation.csv"
eval_csv = pd.read_csv(j_eval_file)
eval_csv.to_csv(eval_name, index=False, encoding = 'utf-8-sig', )
