.PHONY: setup smoke micro tiny tiny100 tiny1000 eval zip clean gpu

setup:
	pip install --upgrade pip
	pip install -r requirements-scale.txt

gpu:
	nvidia-smi || true
	python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda devices:", torch.cuda.device_count())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(i, torch.cuda.get_device_name(i))
PY

smoke:
	python train_moc_federation_parallel.py --scale micro --steps 2
	python run_moc_eval.py

micro:
	python train_moc_federation_parallel.py --scale micro --steps 20
	python run_moc_eval.py

tiny100:
	python train_moc_federation_parallel.py --scale tiny --steps 100
	python run_moc_eval.py

tiny:
	python train_moc_federation_parallel.py --scale tiny --steps 1000
	python run_moc_eval.py

tiny1000:
	python train_moc_federation_parallel.py --scale tiny --steps 1000
	python run_moc_eval.py

eval:
	python run_moc_eval.py

zip:
	zip -r henla_moc_scale_run_artifacts.zip \
		checkpoints \
		.benchmark_runs \
		artifacts \
		logs \
		PROJECT_LOG.md \
		README.md \
		configs \
		scripts \
		requirements-scale.txt \
		Makefile \
		*.py \
		core || true

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
