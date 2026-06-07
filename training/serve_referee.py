# serve_referee.py
"""FastAPI server running native PyTorch/Transformers to host the referee adapter.

This provides an OpenAI-compatible /v1/chat/completions endpoint on port 8060,
bypassing vLLM compiled driver compatibility issues while maintaining high performance.
"""

import os
import torch

# Workaround for float8 attribute crash on older PyTorch versions
if not hasattr(torch, "float8_e8m0fnu"):
    setattr(torch, "float8_e8m0fnu", torch.float32)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from transformers import AutoProcessor, AutoModelForImageTextToText
from peft import PeftModel

app = FastAPI(title="Referee SFT Server")

MODEL_ID = "google/gemma-4-E4B-it"
ADAPTER_PATH = "./referee_lora_output/referee_agent/referee_agent"
PORT = 8060

print("⏳ Loading base model and processor on GPU...")
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained(MODEL_ID)

print(f"⏳ Loading Referee LoRA adapter from {ADAPTER_PATH}...")
model = PeftModel.from_pretrained(model, ADAPTER_PATH, adapter_name="referee_roast")
model.eval()

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    messages = payload.get("messages", [])
    
    # Format using chat template
    if hasattr(processor, "tokenizer") and hasattr(processor.tokenizer, "apply_chat_template"):
        prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
    inputs = processor(text=prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=80,
            temperature=0.1,  # Keep temperature low for deterministic JSON formats
            do_sample=False
        )
        
    # Trim inputs
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    response_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0].strip()
    
    return JSONResponse({
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": response_text
                }
            }
        ]
    })

if __name__ == "__main__":
    print(f"🚀 Referee server listening on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
