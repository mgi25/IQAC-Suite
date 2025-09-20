from typing import List

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = r"C:\\Users\\mgial\\OneDrive\\Desktop\\IQAC-Suite\\Qwen2.5-7B-Instruct-1M"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    trust_remote_code=True,
    torch_dtype=dtype,
)
model.to(device)
model.eval()

app = FastAPI()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: int = 256
    temperature: float = 0.7


@app.post("/v1/chat/completions")
def chat(req: ChatRequest):
    max_tokens = min(req.max_tokens, 256)
    system = ""
    user = []
    for m in req.messages:
        if m.role == "system":
            system = m.content
        elif m.role == "user":
            user.append(m.content)
    prompt = (system + "\n" + "\n".join(user)).strip()
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=req.temperature,
        )
    text = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True
    )
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("local_ai_server:app", host="127.0.0.1", port=8000)
