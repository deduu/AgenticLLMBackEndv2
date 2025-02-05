import torch
from transformers import pipeline
# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

# model_id = "meta-llama/Llama-3.2-1B-Instruct"
model_id = "meta-llama/Llama-3.1-8B-Instruct"



# pipe = pipeline(
#     "text-generation",
#     model=model_id,
#     torch_dtype=torch.bfloat16,
#     device_map="auto",
# )

# text="I'm going through some things with my feelings and myself. I barely sleep and I do nothing but think about how I'm worthless and how I shouldn't be here. I've never tried or contemplated suicide. I've always wanted to fix my issues, but I never get around to it. How can I change my feeling of being worthless to everyone?"

# messages = [
#     {"role": "system", "content": "You are a helpful assistant."},
#     {"role": "user", "content": text},
# ]
# outputs = pipe(
#     messages,
#     max_new_tokens=512,
# )
# print(outputs[0]["generated_text"][-1])

device = torch.device("cuda:6")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16).to(device)


text="I'm going through some things with my feelings and myself. I barely sleep and I do nothing but think about how I'm worthless and how I shouldn't be here. I've never tried or contemplated suicide. I've always wanted to fix my issues, but I never get around to it. How can I change my feeling of being worthless to everyone?"

messages = [
    {"role": "system", "content": "Summarize the following conversation history in a brief without losing any context in a paragraph no more than 250 words:\n\n"},
    {"role": "user", "content": text},
]

input_ids = tokenizer.apply_chat_template(messages,add_generation_prompt=True, return_dict=True, return_tensors="pt")
inputs = {k: v.to(device) for k, v in input_ids.items()}
            # Move to a specific GPU or CPU
with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=512,
        top_k=50,
        top_p=0.95,
        # eos_token_id=self.tokenizer.eos_token_id,
        # pad_token_id=self.tokenizer.eos_token_id
    )
generated_response = tokenizer.decode(output[0][len(inputs["input_ids"][0]):]).strip().replace('<|eot_id|>', '')

# Cleanup
del input_ids
del inputs
del output
import gc
# Force garbage collection
gc.collect()
torch.cuda.empty_cache()
print(generated_response)