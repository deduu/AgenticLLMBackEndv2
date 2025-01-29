import torch
from transformers import pipeline, AutoModel

model_id = "meta-llama/Llama-3.2-3B-Instruct"

pipe = pipeline(
    "text-generation",
    model=model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
messages = [
    {"role": "system", "content": "You are a helpful assistant!"},
    {"role": "user", "content": "Correct this sentence: Ocotober 31,th 2017: 667 the neighbor of the beast | See the playlist | listen: Pop‑up player!"},
]
outputs = pipe(
    messages,
    max_new_tokens=256,
)
print(outputs[0]["generated_text"][-1])
