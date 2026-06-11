# train_dpo.py
"""DPO (Direct Preference Optimization) training script for Player agent.

This script loads the pre-trained SFT model and its adapter, creates
a duplicate frozen reference model (sharing quantized base model weight structures
but having its SFT adapter state locked), and trains the active adapter via DPOTrainer
using the preference paired dataset.
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
from peft import LoraConfig, PeftModel
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import DPOTrainer

try:
    from trl import DPOConfig
except ImportError:
    DPOConfig = None

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
    """Orchestrates the DPO alignment pipeline for the player agent."""
    parser = argparse.ArgumentParser(description="Run DPO alignment training for Player agent.")
    parser.add_argument("--dpo_dataset", type=str, default="data/player/player_dpo.json", help="Path to the JSON preference dataset.")
    parser.add_argument("--output_dir", type=str, default="./player_lora_output/player_agent_dpo", help="Output directory for DPO weights.")
    parser.add_argument("--learning_rate", type=float, default=5e-5, help="Learning rate for AdamW optimizer.")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO temperature margin beta parameter.")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs.")
    parser.add_argument("--batch_size", type=int, default=2, help="Per device training batch size.")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Gradient accumulation steps.")
    args = parser.parse_args()

    set_training_seeds(TRAINING_REPRODUCIBILITY_SEED)

    print("🚀 Initializing DPO Training Pipeline...")
    model_id = "google/gemma-4-E4B-it"
    adapter_path = "./player_lora_output/player_agent_sft_v2/player_agent_sft_v2"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # 1. Load active training model (Quantized Base + Trainable PEFT Adapter)
    print("🤖 Loading active policy model...")
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)
    tokenizer = processor.tokenizer
    
    # Check if EOS token is set, otherwise default to tokenizer settings
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Target language model projection layers strictly (excluding audio/vision towers)
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

    # Wrap model with the pre-trained SFT weights as DPO initialization
    model = PeftModel.from_pretrained(
        model,
        adapter_path,
        is_trainable=True,
        adapter_name="default"
    )
    # Ensure LoRA parameters are trainable
    for param in model.parameters():
        if param.requires_grad:
            pass # Keep trainable parameter gradients open
    
    print("📋 Policy model parameters wrapped successfully.")
    model.print_trainable_parameters()

    # 2. Load duplicate reference model (Quantized Base + Frozen PEFT Adapter)
    print("🤖 Loading reference policy model...")
    ref_model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    ref_model = PeftModel.from_pretrained(
        ref_model,
        adapter_path,
        is_trainable=False,
        adapter_name="default"
    )
    ref_model.eval()
    print("📋 Reference model locked (all parameters frozen).")

    # 3. Load preference dataset
    print(f"📂 Loading preference dataset from: {args.dpo_dataset}")
    dataset = load_dataset("json", data_files={"train": args.dpo_dataset})

    # 4. Set training configurations
    if DPOConfig is not None:
        try:
            training_args = DPOConfig(
                output_dir=args.output_dir,
                per_device_train_batch_size=args.batch_size,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                learning_rate=args.learning_rate,
                beta=args.beta,
                num_train_epochs=args.epochs,
                bf16=True,
                logging_steps=5,
                save_strategy="no",
                optim="paged_adamw_8bit",
                remove_unused_columns=False
            )
        except TypeError:
            training_args = TrainingArguments(
                output_dir=args.output_dir,
                per_device_train_batch_size=args.batch_size,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                learning_rate=args.learning_rate,
                num_train_epochs=args.epochs,
                bf16=True,
                logging_steps=5,
                save_strategy="no",
                optim="paged_adamw_8bit",
                remove_unused_columns=False
            )
    else:
        training_args = TrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            learning_rate=args.learning_rate,
            num_train_epochs=args.epochs,
            bf16=True,
            logging_steps=5,
            save_strategy="no",
            optim="paged_adamw_8bit",
            remove_unused_columns=False
        )

    # 5. Initialize DPOTrainer
    print("🔥 Launching DPOTrainer...")
    import inspect
    
    dpo_kwargs = {
        "model": model,
        "ref_model": ref_model,
        "args": training_args,
        "train_dataset": dataset["train"],
    }
    
    # Use inspect.signature to dynamically map parameters based on local TRL version
    sig = inspect.signature(DPOTrainer.__init__)
    
    # 1. Bind tokenizer / processing_class
    if "processing_class" in sig.parameters:
        dpo_kwargs["processing_class"] = tokenizer
        print("  - Binding tokenizer to 'processing_class' argument based on TRL API signature.")
    else:
        dpo_kwargs["tokenizer"] = tokenizer
        print("  - Binding tokenizer to 'tokenizer' argument based on TRL API signature.")
        
    # 2. Bind beta parameter (only if expected directly by __init__)
    if "beta" in sig.parameters:
        dpo_kwargs["beta"] = args.beta
        print("  - Binding beta directly to DPOTrainer.")
    else:
        print("  - Beta parameter will be read from DPOConfig configuration.")
        
    # 3. Bind length constraints (only if expected directly by __init__)
    if "max_length" in sig.parameters:
        dpo_kwargs["max_length"] = 512
        print("  - Setting max_length=512 on DPOTrainer.")
    if "max_prompt_length" in sig.parameters:
        dpo_kwargs["max_prompt_length"] = 256
        print("  - Setting max_prompt_length=256 on DPOTrainer.")
        
    trainer = DPOTrainer(**dpo_kwargs)

    # 6. Execute DPO training
    print("🏃 Training active adapter via direct preference optimization...")
    trainer.train()

    # 7. Save updated DPO adapter
    dpo_save_path = os.path.join(args.output_dir, "player_agent_dpo")
    model.save_pretrained(dpo_save_path)
    print(f"🎉 DPO Alignment training complete. Saved adapter to: {dpo_save_path}")


if __name__ == "__main__":
    main()
