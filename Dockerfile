FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /workspace/HENLA

RUN apt-get update && apt-get install -y \
    git \
    curl \
    zip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-scale.txt /workspace/HENLA/requirements-scale.txt

RUN pip install --upgrade pip && \
    pip install -r requirements-scale.txt

COPY . /workspace/HENLA

ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false

CMD ["bash"]
