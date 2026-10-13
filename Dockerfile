# syntax=docker/dockerfile:1
#
# Local smoke-test container for the VELARA Launch Risk Assessment submission.
#
# Build:
#   docker build -t velara-analysis .
# Run:
#   docker run --rm -v $(pwd)/dataset:/pack velara-analysis python3 solve.py /pack

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3-pip \
        ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python3.11"]
CMD ["solve.py", "/pack"]
