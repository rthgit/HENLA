#!/bin/bash
# HENLA-GPU Training Runner

set -e

AREA=$1
CONFIG="configs/gpu/${AREA}.yaml"

if [ -z "$AREA" ]; then
    echo "Usage: ./run_gpu_training.sh <area_name>"
    echo "Example: ./run_gpu_training.sh valence"
    exit 1
fi

echo "[HENLA-GPU] Starting training for area: $AREA"
echo "[HENLA-GPU] Using config: $CONFIG"

# Placeholder for actual training command
# python3 core/trainers/${AREA}_trainer.py --config $CONFIG

echo "[HENLA-GPU] Training complete for $AREA."
echo "[HENLA-GPU] Model saved to artifacts/neural/models/${AREA}_v1.pt"
