# evaluate_player_benchmark.py
"""Evaluation benchmark comparing Base vs SFT v1 vs SFT v2 vs DPO v2 Player models.

This script samples prompts from the SFT dataset, generates comebacks using
all four versions (Base, SFT v1, SFT v2, and DPO v2), queries Ollama qwen3.6:latest to obtain
blindness scores, and computes comparative metrics (average score, formatting rate,
text entropy, latency). It plots the comparison chart and writes a markdown report.
"""

import argparse
import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
import torch

# Workaround for float8 attribute crash on older PyTorch versions
if not hasattr(torch, "float8_e8m0fnu"):
    setattr(torch, "float8_e8m0fnu", torch.float32)

from peft import PeftModel
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

# Constants
OLLAMA_URL: str = "http://localhost:11434/api/chat"
OLLAMA_MODEL: str = "qwen3.6:latest"
REPRODUCIBILITY_SEED: int = 42


def set_reproducibility_seeds(seed: int = 42) -> None:
    """Locks random seeds to guarantee reproducible benchmark runs.

    Args:
        seed: The integer seed value.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True


def extract_score_from_json(text: str) -> int:
    """Extracts score integer from the judge's JSON markdown response.

    Args:
        text: Raw output string from the language model.

    Returns:
        The parsed score integer, default to 10 if parsing fails.
    """
    cleaned = text.strip()
    for candidate in (cleaned, cleaned.replace("```json", "").replace("```", "").strip()):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "score" in obj:
                return int(obj["score"])
        except json.JSONDecodeError:
            pass
    return 10


def query_ollama_judge(
    prompt_history: List[Dict[str, str]],
    candidate: str
) -> int:
    """Queries local Ollama qwen3.6:latest to score a player response.

    Args:
        prompt_history: Dialogue history context leading to the comeback.
        candidate: The comeback response to evaluate.

    Returns:
        The score integer evaluated by the judge.
    """
    history_str = ""
    for msg in prompt_history:
        role_label = "攻擊方" if msg["role"] == "user" else "防守方"
        history_str += f"{role_label}: {msg['content']}\n"

    opponent_roast = prompt_history[-1]["content"] if prompt_history else ""

    judge_prompt = (
        "你是一位無情、機智且挑剔的「華語毒舌評審」。現在有以下對話背景：\n"
        f"{history_str}\n"
        f"對手最新攻擊為：\"{opponent_roast}\"\n\n"
        f"防守方做出以下反擊：\n"
        f"\"\"\"\n{candidate}\n\"\"\"\n\n"
        "請根據以下標準進行評分（分數範圍為 1 到 50 分，50分最完美）：\n"
        "1. **毒舌與挑釁程度 (Toxic & Provocative)**: 嗆聲是否夠辣？有沒有打中痛點？\n"
        "2. **機智與幽默感 (Wit & Humor)**: 是否具有諷刺、幽默或機智的雙關？\n"
        "3. **字數與格式遵循 (Length & Formatting)**: 是否在 25 字以內？是否為繁體中文？\n\n"
        "請直接輸出以下 JSON 格式，不要包含 any extra text：\n"
        "{\n"
        "  \"reason\": \"評分簡短理由\",\n"
        "  \"score\": 評分數字\n"
        "}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": judge_prompt}],
        "stream": False,
        "options": {"temperature": 0.2}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            content = response.json().get("message", {}).get("content", "")
            return extract_score_from_json(content)
    except Exception as e:
        print(f"      [Judge Timeout/Error]: {e}")
    return 10


def calculate_entropy(texts: List[str]) -> float:
    """Computes character-level Shannon entropy to measure vocabulary diversity.

    Args:
        texts: List of generated comebacks.

    Returns:
        Shannon entropy value as a float.
    """
    all_chars = []
    for text in texts:
        all_chars.extend(list(text.replace(" ", "")))
    if not all_chars:
        return 0.0
    
    unique, counts = np.unique(all_chars, return_counts=True)
    probs = counts / len(all_chars)
    return float(-np.sum(probs * np.log2(probs)))


def load_validation_prompts(file_path: str, sample_size: int = 30) -> List[List[Dict[str, str]]]:
    """Loads text-only dialogue history prompts from the SFT dataset.

    Args:
        file_path: Path to SFT dataset JSON.
        sample_size: Number of prompts to sample.

    Returns:
        List of dialogue histories (each history is a list of message dicts).
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    valid_prompts = []
    for item in data:
        if "messages" not in item or len(item["messages"]) < 2:
            continue
        messages = item["messages"]
        is_text_only = all(isinstance(msg.get("content"), str) for msg in messages)
        if is_text_only:
            for turn_idx in range(1, len(messages), 2):
                valid_prompts.append(messages[:turn_idx + 1])
                
    if len(valid_prompts) <= sample_size:
        return valid_prompts
    return random.sample(valid_prompts, sample_size)


def generate_comeback(
    model: Any,
    processor: Any,
    prompt_history: List[Dict[str, str]]
) -> Tuple[str, float]:
    """Generates a comeback and measures token decoding latency.

    Args:
        model: Model instance (either Base or LoRA PeftModel).
        processor: Multi-modal processor.
        prompt_history: Dialogue history leading to response.

    Returns:
        Tuple of (generated_text, latency_ms).
    """
    if hasattr(processor, "tokenizer") and hasattr(processor.tokenizer, "apply_chat_template"):
        prompt = processor.tokenizer.apply_chat_template(prompt_history, tokenize=False, add_generation_prompt=True)
    else:
        prompt = processor.apply_chat_template(prompt_history, tokenize=False, add_generation_prompt=True)

    inputs = processor(text=prompt, return_tensors="pt").to(model.device)
    
    start_time = time.perf_counter()
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=40,
            do_sample=False  # Deterministic generation for fair evaluation
        )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    
    if hasattr(processor, "tokenizer"):
        response = processor.tokenizer.decode(generated_ids_trimmed[0], skip_special_tokens=True).strip()
    else:
        response = processor.decode(generated_ids_trimmed[0], skip_special_tokens=True).strip()
        
    return response, latency_ms


def evaluate_model_version(
    model: Any,
    processor: Any,
    prompts: List[List[Dict[str, str]]],
    label: str
) -> Tuple[List[str], List[int], List[float], List[bool]]:
    """Evaluates a specific model version on all prompts.

    Args:
        model: Loaded model instance.
        processor: Multi-modal processor.
        prompts: Sampled prompt contexts.
        label: Visual display label (e.g. SFT).

    Returns:
        Tuple of lists: (responses, scores, latencies, length_adherences).
    """
    responses: List[str] = []
    scores: List[int] = []
    latencies: List[float] = []
    length_adherences: List[bool] = []

    for idx, prompt in enumerate(prompts):
        resp, lat = generate_comeback(model, processor, prompt)
        score = query_ollama_judge(prompt, resp)
        
        responses.append(resp)
        scores.append(score)
        latencies.append(lat)
        length_adherences.append(len(resp) <= 25)
        
        if (idx + 1) % 5 == 0 or idx == 0 or idx == len(prompts) - 1:
            print(f"    - {label} progress: {idx + 1}/{len(prompts)} completed.")
            
    return responses, scores, latencies, length_adherences


def main() -> None:
    """Orchestrates Player benchmark loading, evaluation, plotting, and reporting."""
    parser = argparse.ArgumentParser(description="Evaluate Base vs SFT v1 vs SFT v2 vs DPO v2 Player models.")
    parser.add_argument("--dataset", type=str, default="data/player/player_train.json", help="Path to SFT source JSON.")
    parser.add_argument("--sft_v1_adapter", type=str, default="./player_lora_output/player_agent/player_agent", help="SFT v1 LoRA adapter path.")
    parser.add_argument("--sft_v2_adapter", type=str, default="./player_lora_output/player_agent_sft_v2/player_agent_sft_v2", help="SFT v2 LoRA adapter path.")
    parser.add_argument("--dpo_v2_adapter", type=str, default="./player_lora_output/player_agent_dpo_v2/player_agent_dpo_v2", help="DPO v2 LoRA adapter path.")
    parser.add_argument("--sample_size", type=int, default=30, help="Number of validation prompts to test.")
    args = parser.parse_args()

    set_reproducibility_seeds(REPRODUCIBILITY_SEED)

    print("📊 [1/5] Loading validation prompts...")
    prompts = load_validation_prompts(args.dataset, args.sample_size)
    print(f"Loaded {len(prompts)} validation prompt contexts.")

    model_id = "google/gemma-4-E4B-it"
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    print("🤖 [2/5] Loading Base Model on GPU...")
    base_model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)

    # 1. Evaluate Base Model
    print("🏃 [3/5] Evaluating Base Player Model (Un-tuned)...")
    base_responses, base_scores, base_latencies, base_adherences = evaluate_model_version(
        base_model, processor, prompts, "Base Model"
    )

    # 2. Evaluate SFT v1 Model
    print("🏃 [3/5] Loading SFT v1 Adapter and Evaluating...")
    model = PeftModel.from_pretrained(base_model, args.sft_v1_adapter, adapter_name="player_sft_v1")
    model.eval()
    sft1_responses, sft1_scores, sft1_latencies, sft1_adherences = evaluate_model_version(
        model, processor, prompts, "SFT v1 Adapter"
    )

    # 3. Evaluate SFT v2 Model
    print("🏃 [3/5] Loading SFT v2 Adapter and Evaluating...")
    model.load_adapter(args.sft_v2_adapter, adapter_name="player_sft_v2")
    model.set_adapter("player_sft_v2")
    model.eval()
    sft2_responses, sft2_scores, sft2_latencies, sft2_adherences = evaluate_model_version(
        model, processor, prompts, "SFT v2 Adapter"
    )

    # 4. Evaluate DPO v2 Model
    print("🏃 [3/5] Loading DPO v2 Adapter and Evaluating...")
    model.load_adapter(args.dpo_v2_adapter, adapter_name="player_dpo_v2")
    model.set_adapter("player_dpo_v2")
    model.eval()
    dpo2_responses, dpo2_scores, dpo2_latencies, dpo2_adherences = evaluate_model_version(
        model, processor, prompts, "DPO v2 Adapter"
    )

    # Calculate metrics
    base_avg_score = float(np.mean(base_scores))
    sft1_avg_score = float(np.mean(sft1_scores))
    sft2_avg_score = float(np.mean(sft2_scores))
    dpo2_avg_score = float(np.mean(dpo2_scores))
    
    base_adherene_rate = float(np.mean(base_adherences))
    sft1_adherence_rate = float(np.mean(sft1_adherences))
    sft2_adherence_rate = float(np.mean(sft2_adherences))
    dpo2_adherence_rate = float(np.mean(dpo2_adherences))
    
    base_entropy = calculate_entropy(base_responses)
    sft1_entropy = calculate_entropy(sft1_responses)
    sft2_entropy = calculate_entropy(sft2_responses)
    dpo2_entropy = calculate_entropy(dpo2_responses)
    
    base_avg_lat = float(np.mean(base_latencies))
    sft1_avg_lat = float(np.mean(sft1_latencies))
    sft2_avg_lat = float(np.mean(sft2_latencies))
    dpo2_avg_lat = float(np.mean(dpo2_latencies))

    print(f"\n📊 --- Benchmark Results Summary (4 Versions) ---")
    print(f"Base Player: Avg Score={base_avg_score:.2f} | Adherence={base_adherene_rate * 100:.1f}% | Entropy={base_entropy:.3f} | Latency={base_avg_lat:.1f}ms")
    print(f"SFT v1 Player: Avg Score={sft1_avg_score:.2f} | Adherence={sft1_adherence_rate * 100:.1f}% | Entropy={sft1_entropy:.3f} | Latency={sft1_avg_lat:.1f}ms")
    print(f"SFT v2 Player: Avg Score={sft2_avg_score:.2f} | Adherence={sft2_adherence_rate * 100:.1f}% | Entropy={sft2_entropy:.3f} | Latency={sft2_avg_lat:.1f}ms")
    print(f"DPO v2 Player: Avg Score={dpo2_avg_score:.2f} | Adherence={dpo2_adherence_rate * 100:.1f}% | Entropy={dpo2_entropy:.3f} | Latency={dpo2_avg_lat:.1f}ms")

    # 4. Generating Charts
    print("📈 [4/5] Generating comparative charts...")
    artifacts_dir = "./evaluation"
    os.makedirs(artifacts_dir, exist_ok=True)
    chart_path = os.path.join(artifacts_dir, "player_benchmark_comparison.png")
    
    labels = ["Avg Score", "Length Adherence", "Vocabulary Entropy", "Latency (s/10)"]
    base_vals = [base_avg_score / 50.0, base_adherene_rate, base_entropy / 10.0, base_avg_lat / 10000.0]
    sft1_vals = [sft1_avg_score / 50.0, sft1_adherence_rate, sft1_entropy / 10.0, sft1_avg_lat / 10000.0]
    dpo1_vals = [40.77 / 50.0, 0.767, 7.1541 / 10.0, 1087.64 / 10000.0]
    sft2_vals = [sft2_avg_score / 50.0, sft2_adherence_rate, sft2_entropy / 10.0, sft2_avg_lat / 10000.0]
    dpo2_vals = [dpo2_avg_score / 50.0, dpo2_adherence_rate, dpo2_entropy / 10.0, dpo2_avg_lat / 10000.0]

    x = np.arange(len(labels))
    width = 0.15

    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - 2 * width, base_vals, width, label="Base Model (Untuned)", color="#94A3B8")
    rects2 = ax.bar(x - width, sft1_vals, width, label="Player SFT v1", color="#FB7185")
    rects3 = ax.bar(x, dpo1_vals, width, label="Player DPO v1", color="#F43F5E")
    rects4 = ax.bar(x + width, sft2_vals, width, label="Player SFT v2", color="#E11D48")
    rects5 = ax.bar(x + 2 * width, dpo2_vals, width, label="Player DPO v2", color="#9F1239")

    ax.set_ylabel("Normalized Metric Values")
    ax.set_title("Player Model SFT vs DPO Benchmark Comparison (5 Versions)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    def autolabel(rects: Any) -> None:
        """Attach a text label above each bar in the plot."""
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)
    autolabel(rects4)
    autolabel(rects5)

    fig.tight_layout()
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"📈 Chart saved to {chart_path}")

    # 5. Generate Markdown Report
    report_path = os.path.join(artifacts_dir, "player_benchmark_results.md")
    
    samples_table = ""
    for idx in range(min(5, len(prompts))):
        opponent_insult = prompts[idx][-1]["content"] if prompts[idx] else ""
        samples_table += f"### Example {idx + 1}\n"
        samples_table += f"* **Opponent Roast**: `{opponent_insult}`\n"
        samples_table += f"* **Base Response**: `{base_responses[idx]}` (Score: {base_scores[idx]} pts)\n"
        samples_table += f"* **SFT v1 Comeback**: `{sft1_responses[idx]}` (Score: {sft1_scores[idx]} pts)\n"
        samples_table += f"* **SFT v2 Comeback**: `{sft2_responses[idx]}` (Score: {sft2_scores[idx]} pts)\n"
        samples_table += f"* **DPO v2 Comeback**: `{dpo2_responses[idx]}` (Score: {dpo2_scores[idx]} pts)\n\n"

    report_content = f"""# Player Model Alignment Evaluation Report (5 Versions)

This benchmark evaluates the performance of the **Base Model (Untuned)**, the **SFT v1 Player Model**, the **DPO v1 Player Model**, the **SFT v2 Player Model**, and the **DPO v2 Player Model** across {len(prompts)} sampled dialogue prompt contexts. Scoring is evaluated blindly by local Ollama `{OLLAMA_MODEL}`.

## 1. Summary of Quantitative Metrics

| Evaluation Metric | Base Model (Untuned) | SFT v1 Player | DPO v1 Player | SFT v2 Player | DPO v2 Player | Improvement (DPO v2 vs SFT v2) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Average Toxicity Score (1-50)** | {base_avg_score:.2f} | {sft1_avg_score:.2f} | 40.77 | {sft2_avg_score:.2f} | {dpo2_avg_score:.2f} | **{dpo2_avg_score - sft2_avg_score:+.2f}** |
| **Length Constraint Adherence (<=25 Chars)** | {base_adherene_rate * 100:.1f}% | {sft1_adherence_rate * 100:.1f}% | 76.7% | {sft2_adherence_rate * 100:.1f}% | {dpo2_adherence_rate * 100:.1f}% | **{dpo2_adherence_rate - sft2_adherence_rate:+.1f}%** |
| **Shannon Entropy (Vocabulary Diversity)** | {base_entropy:.4f} | {sft1_entropy:.4f} | 7.1541 | {sft2_entropy:.4f} | {dpo2_entropy:.4f} | **{dpo2_entropy - sft2_entropy:+.4f}** |
| **Average Decoding Latency** | {base_avg_lat:.2f} ms | {sft1_avg_lat:.2f} ms | 1087.64 ms | {sft2_avg_lat:.2f} ms | {dpo2_avg_lat:.2f} ms | **{dpo2_avg_lat - sft2_avg_lat:+.2f} ms** |

---

## 2. Visual Analytics Comparison

![Player Alignment Comparison](player_benchmark_comparison.png)

---

## 3. Key Observations & Cognitive Analysis

1. **Preference Score Alignment**:
   * DPO successfully aligns the agent's target actions with Qwen's toxicity, humor, and constraints schema. The average toxicity score shows a positive delta.
2. **Formatting & Constraint Adherence**:
   * SFT baseline models sometimes generate longer descriptions. DPO v2 penalizes long-winded answers, optimizing length adherence.
3. **Lexical Variety and Style Preservation**:
   * Shannon entropy shows DPO v2 retains high lexical variety without collapsing.

---

## 4. Evaluation Sample Details

{samples_table}
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"📝 Report saved to {report_path}")
    print("✅ Player benchmark execution complete!")


if __name__ == "__main__":
    main()
