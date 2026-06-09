# train_referee_v2.py
"""SFT Training script for Referee v2 agent.

This script loads the base model google/gemma-4-E4B-it, sets up a clean LoRA
configuration targeting the language model layers, and trains the referee adapter
on the new Qwen-generated high-quality dataset (data/referee/referee_train_v2.json).
"""

import argparse
import os
import random
from typing import List

import numpy as np
import torch
# Workaround for float8 attribute crash on older PyTorch versions
if not hasattr(torch, "float8_e8m0fnu"):
    setattr(torch, "float8_e8m0fnu", torch.float32)

from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
    TrainingArguments,
)
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


def main() -> None:
    """Orchestrates SFT training pipeline for the Referee v2 adapter."""
    parser = argparse.ArgumentParser(description="Train Referee v2 model on Qwen-distilled dataset.")
    parser.add_argument("--dataset_path", type=str, default="data/referee/referee_train_v2.json", help="Path to Referee v2 JSON dataset.")
    parser.add_argument("--output_dir", type=str, default="./referee_lora_output/referee_agent_v2", help="Output directory to save adapter weights.")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate for AdamW.")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs.")
    parser.add_argument("--batch_size", type=int, default=2, help="Batch size per device.")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Gradient accumulation steps.")
    args = parser.parse_args()

    set_training_seeds(TRAINING_REPRODUCIBILITY_SEED)

    print("🚀 Initializing Referee v2 SFT Training Pipeline...")
    model_id = "google/gemma-4-E4B-it"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # 1. Load Quantized Base Model
    print("🤖 Loading base model on GPU...")
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)
    tokenizer = processor.tokenizer

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2. Define LoRA parameters targeting language model projection layers
    target_modules = ".*language_model.*(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=target_modules,
        exclude_modules=["vision_tower", "audio_tower"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    # Wrap model with Referee v2 target adapter
    model = get_peft_model(model, peft_config, adapter_name="referee_agent_v2")
    model.print_trainable_parameters()

    # 3. Load SFT dataset
    print(f"📂 Loading Referee v2 dataset from: {args.dataset_path}")
    dataset = load_dataset("json", data_files={"train": args.dataset_path})

    # Custom conversational formatting function using processor apply_chat_template
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

    # 4. Set SFTConfig / TrainingArguments
    if SFTConfig is not None:
        try:
            training_args = SFTConfig(
                output_dir=args.output_dir,
                per_device_train_batch_size=args.batch_size,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                learning_rate=args.learning_rate,
                bf16=True,
                logging_steps=10,
                save_strategy="no",
                optim="paged_adamw_8bit",
                max_length=512,
                num_train_epochs=args.epochs,
                remove_unused_columns=False
            )
        except TypeError:
            training_args = SFTConfig(
                output_dir=args.output_dir,
                per_device_train_batch_size=args.batch_size,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                learning_rate=args.learning_rate,
                bf16=True,
                logging_steps=10,
                save_strategy="no",
                optim="paged_adamw_8bit",
                max_seq_length=512,
                num_train_epochs=args.epochs,
                remove_unused_columns=False
            )
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            formatting_func=formatting_prompts_func,
            args=training_args
        )
    else:
        training_args = TrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            learning_rate=args.learning_rate,
            bf16=True,
            logging_steps=10,
            save_strategy="no",
            optim="paged_adamw_8bit",
            num_train_epochs=args.epochs,
            remove_unused_columns=False
        )
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            max_seq_length=512,
            formatting_func=formatting_prompts_func,
            args=training_args
        )

    # 5. Execute SFT training
    print("🏃 Training Referee v2 adapter...")
    trainer.train()

    # 6. Save target adapter weights
    save_path = os.path.join(args.output_dir, "referee_agent_v2")
    model.save_pretrained(save_path)
    print(f"🎉 Successfully trained and saved adapter referee_agent_v2 to: {save_path}")


if __name__ == "__main__":
    main()
