import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

model_name = "Qwen/Qwen3-32B-AWQ" # Qwen/Qwen3-32B

tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
)

messages = [
    {"role": "user", "content": "Who are you?"}
]

inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=50,
        do_sample=True,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
    )

new_tokens = outputs[0][inputs["input_ids"].shape[-1]:]

print("token ids:", new_tokens.tolist())
print(
    "output:",
    tokenizer.decode(new_tokens, skip_special_tokens=True)
)

