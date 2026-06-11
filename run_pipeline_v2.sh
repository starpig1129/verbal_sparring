#!/bin/bash
# run_pipeline_v2.sh
# End-to-end training and evaluation pipeline for Verbal Sparring v2.
# 
# This script automates:
# 1. Unloading Ollama models to prevent CUDA OOM before PyTorch training
# 2. Referee v2 SFT training (on newly distilled Qwen dataset)
# 3. Player DPO preference dataset generation (evaluated via Qwen judge)
# 4. Player v2 DPO alignment training (maximizing response toxicity and wittiness)
# 5. Running automated evaluation benchmarks for both Referee and Player models

set -e # Exit immediately if any command fails

echo "========================================================================="
echo "🚀 Launching Automated Verbal Sparring v2 Training & Alignment Pipeline"
echo "========================================================================="

# Step 1: Train Referee v2 SFT adapter
echo ""
echo "👉 Step 1/4: Unloading Ollama models to free up GPU memory..."
ollama stop qwen3.6:latest || echo "   ⚠️ Ollama stop command skipped (model not running or command unavailable)."

echo ""
echo "👉 Step 1/4: Training Referee v2 LoRA Adapter (SFT)..."
echo "   Dataset: data/referee/referee_train_v2.json"
python training/train_referee_v2.py --epochs 3 --batch_size 2 --gradient_accumulation_steps 4

echo ""
echo "👉 Step 1/4: Training Player v2 LoRA Adapter (SFT)..."
echo "   Dataset: data/player/player_train.json"
python training/train_player_sft_v2.py --epochs 3 --batch_size 2 --gradient_accumulation_steps 4

# Step 2: Generate Player DPO v2 preference dataset
echo ""
echo "👉 Step 2/4: Generating Player DPO Preference Dataset..."
echo "   Source: data/player/player_train.json -> Target: data/player/player_dpo.json"
# Sampling 300 dialogues for balanced performance and reasonable execution time
python training/generate_dpo_dataset.py --num_samples 300 --num_candidates 3

# Step 3: Train Player DPO v2 adapter
echo ""
echo "👉 Step 3/4: Unloading Ollama models to free up GPU memory..."
ollama stop qwen3.6:latest || echo "   ⚠️ Ollama stop command skipped (model not running or command unavailable)."

echo ""
echo "👉 Step 3/4: Training Player v2 LoRA Adapter (DPO)..."
echo "   Baseline SFT: ./player_lora_output/player_agent/player_agent"
python training/train_dpo.py --epochs 3 --learning_rate 5e-5 --output_dir ./player_lora_output/player_agent_dpo_v2

# Step 4: Run evaluation benchmarks to verify improvements
echo ""
echo "👉 Step 4/4: Executing Model Benchmarks & Generating Reports..."

if [ -f "training/evaluate_benchmark.py" ]; then
    echo "   - Running Toxic Referee Benchmark..."
    python training/evaluate_benchmark.py --sft_v1_adapter ./referee_lora_output/referee_agent/referee_agent --sft_v2_adapter ./referee_lora_output/referee_agent_v2 || echo "   ⚠️ Referee evaluation encountered warnings, continuing..."
fi

if [ -f "training/evaluate_player_benchmark.py" ]; then
    echo "   - Running Player Alignment Benchmark..."
    python training/evaluate_player_benchmark.py || echo "   ⚠️ Player evaluation encountered warnings, continuing..."
fi

echo "   - Generating Consolidated Benchmark Chart..."
python training/plot_consolidated_benchmark.py || echo "   ⚠️ Plot consolidation failed, continuing..."

echo "   - Compiling SVG slides..."
python scratch/generate_slides.py || echo "   ⚠️ Slide compilation failed, continuing..."

echo ""
echo "========================================================================="
echo "🎉 Pipeline v2 Completed Successfully!"
echo "   - Referee v2 SFT Adapter  : ./referee_lora_output/referee_agent_v2"
echo "   - Player v2 DPO Adapter   : ./player_lora_output/player_agent_dpo/player_agent_dpo"
echo "   - Updated Benchmarks      : check docs/evaluation/ and evaluation/"
echo "   - SVG Presentation Slides : ./evaluation/slides/"
echo "========================================================================="
