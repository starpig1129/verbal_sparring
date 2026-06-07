#!/bin/bash
# serve_adversarial.sh
# Starts the PyTorch/Transformers FastAPI server serving google/gemma-4-E4B-it with the referee adapter.

# Enforce script error trapping
set -euo pipefail

MODEL_PATH="google/gemma-4-E4B-it"
ADAPTER_PATH="./referee_lora_output/referee_agent"
PORT=8060

echo "🚀 Launching Native PyTorch Referee Server on Port ${PORT}..."
echo "Model: ${MODEL_PATH}"
echo "Adapter Path: ${ADAPTER_PATH}"

# Launch the PyTorch FastAPI referee server
python training/serve_referee.py

