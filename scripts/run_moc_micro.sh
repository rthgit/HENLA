#!/usr/bin/env bash
set -e

mkdir -p logs checkpoints artifacts .benchmark_runs

python train_moc_federation_parallel.py --scale micro --steps 20 \
  2>&1 | tee logs/moc_micro_train.log

python run_moc_eval.py \
  2>&1 | tee logs/moc_micro_eval.log
