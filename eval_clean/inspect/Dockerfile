FROM python:3.12.12-slim

RUN python -m venv /opt/scicode-2024 && \
    /opt/scicode-2024/bin/pip install --no-cache-dir \
    numpy==1.26.4 scipy==1.13.1 sympy==1.13.3 h5py==3.12.1 matplotlib==3.9.4
RUN python -m venv /opt/scicode-2025 && \
    /opt/scicode-2025/bin/pip install --no-cache-dir \
    numpy==2.4.2 scipy==1.17.1 sympy==1.14.0 h5py==3.15.1 matplotlib==3.10.9

COPY vendor/scicode /opt/scicode-vendor/scicode
ENV PYTHONPATH=/opt/scicode-vendor
WORKDIR /workspace
