# train_co_adapters.py
"""Trains Player and Referee LoRA adapters sequentially on a single GPU.

This script implements training loops for both adapters using HuggingFace TRL's
SFTTrainer. This prevents loading redundant base models and reduces VRAM.
"""

import os
import random
from typing import List, Dict, Any
import numpy as np
import torch
# Workaround for float8 attribute crash on older PyTorch versions
if not hasattr(torch, "float8_e8m0fnu"):
    setattr(torch, "float8_e8m0fnu", torch.float32)
from datasets import load_dataset
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer
try:
    from trl import SFTConfig
except ImportError:
    SFTConfig = None


# Seed for training reproducibility
TRAINING_REPRODUCIBILITY_SEED: int = 42

def set_training_seeds(seed: int = 42) -> None:
    """Locks random seeds to guarantee reproducible weight updates.

    Args:
        seed: The integer seed value.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True

def train_adapter(
    model_id: str,
    adapter_name: str,
    dataset_path: str,
    output_dir: str,
    target_modules: List[str]
) -> None:
    """Trains a specific LoRA adapter on a target dataset.

    Args:
        model_id: HuggingFace identifier for base model.
        adapter_name: Label identifier for the LoRA adapter.
        dataset_path: Path to the JSON training dataset.
        output_dir: Output directory path to save model weights.
        target_modules: Layer projection modules to train.
    """
    set_training_seeds(TRAINING_REPRODUCIBILITY_SEED)
    print(f"Starting SFT Training for adapter: {adapter_name}...")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    # Load model and processor
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)
    
    # Define LoRA parameters
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # Wrap model with target adapter name
    model = get_peft_model(model, peft_config, adapter_name=adapter_name)
    model.print_trainable_parameters()
    
    # Load SFT dataset
    dataset = load_dataset("json", data_files={"train": dataset_path})
    
    # Custom conversational formatting function using model processor/tokenizer templates
    # Supports both batched and non-batched mapping inputs
    def formatting_prompts_func(example):
        is_batch = False
        if "messages" in example:
            if len(example["messages"]) > 0 and isinstance(example["messages"][0], list):
                is_batch = True

        def format_single_chat(messages):
            if hasattr(processor, "tokenizer") and hasattr(processor.tokenizer, "apply_chat_template"):
                return processor.tokenizer.apply_chat_template(messages, tokenize=False)
            elif hasattr(processor, "apply_chat_template"):
                return processor.apply_chat_template(messages, tokenize=False)
            else:
                formatted = ""
                for msg in messages:
                    formatted += f"<start_of_turn>{msg['role']}\n{msg['content']}<end_of_turn>\n"
                return formatted

        if is_batch:
            return [format_single_chat(msgs) for msgs in example["messages"]]
        else:
            return format_single_chat(example["messages"])


    # Define SFTConfig if supported, otherwise fallback to TrainingArguments
    if SFTConfig is not None:
        try:
            training_args = SFTConfig(
                output_dir=output_dir,
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
                learning_rate=2e-4,
                bf16=True,
                logging_steps=10,
                save_strategy="no",
                optim="paged_adamw_8bit",
                max_length=512
            )
        except TypeError:
            training_args = SFTConfig(
                output_dir=output_dir,
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
                learning_rate=2e-4,
                bf16=True,
                logging_steps=10,
                save_strategy="no",
                optim="paged_adamw_8bit",
                max_seq_length=512
            )
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            formatting_func=formatting_prompts_func,
            args=training_args
        )
    else: 
        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=10,
            save_strategy="no",
            optim="paged_adamw_8bit"
        )
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            max_seq_length=512,
            formatting_func=formatting_prompts_func,
            args=training_args
        )
    
    trainer.train()
    
    # Save target adapter weights
    model.save_pretrained(os.path.join(output_dir, adapter_name))
    print(f"Successfully trained and saved adapter {adapter_name} to {output_dir}")


if __name__ == "__main__":
    print("🚀 Starting Multi-Adapter Co-Training Pipeline...")
    model_id = "google/gemma-4-E4B-it"
    
    # 1. Train Player Adapter
    train_adapter(
        model_id=model_id,
        adapter_name="player_agent",
        dataset_path="player_train.json",
        output_dir="./player_lora_output",
        target_modules=[
            "q_proj.linear", "k_proj.linear", "v_proj.linear", "o_proj.linear",
            "gate_proj.linear", "up_proj.linear", "down_proj.linear"
        ]
    )
    
    # 2. Train Referee Adapter
    train_adapter(
        model_id=model_id,
        adapter_name="referee_agent",
        dataset_path="referee_train.json",
        output_dir="./referee_lora_output",
        target_modules=[
            "q_proj.linear", "k_proj.linear", "v_proj.linear", "o_proj.linear",
            "gate_proj.linear", "up_proj.linear", "down_proj.linear"
        ]
    )
    
    print("✅ All adapters trained successfully.")

