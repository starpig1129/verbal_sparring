#!/bin/bash
# run_pipeline.sh
# Automated pipeline for Verbal Sparring SFT: Simulation -> Conversion -> Merging -> Training

set -e # Exit immediately if any command fails

echo "========================================================="
echo "🚀 Starting Automated Verbal Sparring SFT Pipeline"
echo "========================================================="

# Step 1: Run adversarial self-play simulation to generate diverse dataset
echo ""
echo "Step 1/4: Running Adversarial Self-Play Simulation..."
python training/adversarial_simulation.py

# Step 2: Convert legacy SFT datasets to style-conditioned multi-turn format
echo ""
echo "Step 2/4: Converting Legacy SFT Datasets..."
python training/convert_existing_dataset.py

# Step 3: Merge and shuffle legacy and simulation datasets
echo ""
echo "Step 3/4: Blending and Shuffling Datasets..."
python training/convert_existing_dataset.py --merge-only

# Step 4: Execute Co-Adapter Training (SFT LoRA for Player and Referee)
echo ""
echo "Step 4/4: Commencing LoRA Co-Adapter Training..."
python training/train_co_adapters.py

echo ""
echo "========================================================="
echo "🎉 SFT Pipeline Completed Successfully!"
echo "========================================================="
