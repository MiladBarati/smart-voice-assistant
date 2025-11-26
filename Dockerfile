FROM nvidia/cuda:11.4.3-cudnn8-runtime-ubuntu20.04

RUN apt-get update && apt-get install -y pciutils wget

CMD ["bash", "-c", "echo '=== GPU Check Inside Container ==='; nvidia-smi"]
