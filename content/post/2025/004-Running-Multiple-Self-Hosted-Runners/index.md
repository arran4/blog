---
title: "Running Multiple Self-Hosted GitHub Actions Runners in a Single Docker-in-Docker Container"
date: 2025-07-05T00:00:00+10:00
draft: false
tags: ["github-actions", "docker", "devops"]
categories: ["devops"]
author: "Arran Ubels"
---

## Introduction

Running dozens of self-hosted GitHub Actions runners can quickly become a management headache. Maintaining separate Docker images for each runner and rebuilding them when GitHub updates the runner software burns time and storage. By leveraging one privileged Docker-in-Docker (DinD) container as a supervisor we can host many lightweight runner containers inside it. This approach isolates configuration per runner, keeps updates simple and avoids rebuilding the entire image each time a new runner version drops.

## Prerequisites

* Docker and Docker Compose installed on the host
* A GitHub repository where self-hosted runners are allowed
* Registration tokens for each runner you intend to create

## Architecture Overview

Within a single `docker:dind` supervisor container we build the runner image at runtime. Individual runner containers mount the DinD socket to use Docker and share a host-mounted config directory so their configuration persists across restarts. A helper script `add-runner.sh` registers new runners dynamically.

```
+---------------------------------------------------------+
| docker:dind supervisor                                  |
|                                                         |
|  +-----------------------------------------------+      |
|  | ubuntu-runner image (built at startup)        |      |
|  +-----------------------------------------------+      |
|   \--> runner containers                         |      |
|        - mount /var/run/docker.sock              |      |
|        - mount /home/runner/configs/<name>       |      |
|        - run with env vars for token & repo URL  |      |
+---------------------------------------------------------+
```

### Handling directory names & rebuilds

Early versions assumed the config directory name was safe to use directly as the container name. When a folder contained hyphens or uppercase letters the supervisor failed with an `invalid reference format` error while trying to restart the runner after an image rebuild. Each runner now stores its GitHub URL and registration token in `.url` and `.token` files so the supervisor can re-create containers automatically. Directory names are normalised to lowercase and any disallowed characters become underscores.

## Step-by-Step Instructions

### DinD Supervisor Dockerfile

```dockerfile
FROM docker:24.0.7-dind
RUN apk add --no-cache bash curl git jq nodejs npm tar openssl shadow sudo
RUN useradd -m -s /bin/bash runner && echo "runner ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
WORKDIR /home/runner
COPY supervisor.sh start-runner.sh Dockerfile.ubuntu-runner /home/runner/
COPY add-runner.sh /usr/local/bin/add-runner
RUN chmod +x /home/runner/*.sh /usr/local/bin/add-runner
ENTRYPOINT ["/home/runner/supervisor.sh"]
```

### Supervisor Script

```bash
#!/bin/bash
set -euxo pipefail

echo "[supervisor] 🔥 Starting Docker daemon..."
dockerd & DOCKERD_PID=$!

echo "[supervisor] ⏳ Waiting for Docker daemon..."
until docker info &>/dev/null; do sleep 1; done
echo "[supervisor] ✅ Docker is ready."

# 1) Fetch & extract runner bits
: "${GH_RUNNER_VERSION:=2.325.0}"
ASSET="actions-runner-linux-x64-${GH_RUNNER_VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${GH_RUNNER_VERSION}/${ASSET}"

echo "[fetcher] 🌐 Downloading runner v${GH_RUNNER_VERSION}…"
curl -sSfL -o "${ASSET}" "${DOWNLOAD_URL}"

echo "[fetcher] 🗜 Extracting to base-runner/"
rm -rf base-runner && mkdir base-runner
tar xzf "${ASSET}" -C base-runner
rm "${ASSET}"
chown -R runner:runner base-runner
echo "[fetcher] ✅ base-runner ready."

# 2) Build the Ubuntu runner image
echo "[builder] 🏗 Building ubuntu-runner image…"
docker build -t ubuntu-runner -f Dockerfile.ubuntu-runner .

# 3) Re-activate all existing configs
echo "[supervisor] 🌱 Re-activating all runners under configs/…"
for dir in /home/runner/configs/*; do
  [[ -d "$dir" ]] || continue
  raw="$(basename "$dir")"
  name="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_]/_/g')"

  # Skip if container already exists
  if docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "[supervisor] ↪ Runner '$name' already exists; skipping"
    continue
  fi

  # Build ENV args only if metadata is present
  env_args=()
  if [[ -r "$dir/.url" && -r "$dir/.token" ]]; then
    env_args+=( -e "RUNNER_REPO_URL=$(<"$dir/.url")" )
    env_args+=( -e "RUNNER_TOKEN=$(<"$dir/.token")" )
  else
    echo "[supervisor] ⚠ No .url/.token for '$raw'; relying on existing credentials"
  fi

  echo "[supervisor] ⇢ Launching runner container '$name'…"
  docker run -d \
    --name "$name" \
    "${env_args[@]}" \
    -e RUNNER_NAME="$name" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$dir":/opt/runner-files \
    ubuntu-runner
done

# 4) Keep supervisor alive until dockerd exits
wait "$DOCKERD_PID"
```

### Ubuntu Runner Dockerfile

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    curl git jq sudo nodejs npm \
    libicu70 libssl-dev libcurl4-openssl-dev \
  && rm -rf /var/lib/apt/lists/*

COPY base-runner /opt/runner-files
WORKDIR /opt/runner-files
RUN sed -i -E \
      -e 's/libssl1\.0\.(2|0|1)/libssl-dev/g' \
      -e 's/libicu7(2|1)/libicu70/g' \
    bin/installdependencies.sh \
  && ./bin/installdependencies.sh

COPY start-runner.sh /usr/local/bin/start-runner
RUN chmod +x /usr/local/bin/start-runner
RUN useradd -m -s /bin/bash runner
USER runner
ENTRYPOINT ["start-runner"]
```

### Runner Wrapper

```bash
#!/bin/bash
set -euxo pipefail
: "${RUNNER_REPO_URL:?RUNNER_REPO_URL is required}"
: "${RUNNER_TOKEN:?RUNNER_TOKEN is required}"
: "${RUNNER_NAME:=runner-$(hostname)}"
cd /opt/runner-files
./config.sh \
  --url "$RUNNER_REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --work _work \
  --unattended \
  --replace
exec ./run.sh
```

### Dynamic Add-Runner Helper

```bash
#!/bin/bash
set -euxo pipefail

usage(){
  echo "Usage: add-runner --url <repo_url> --token <reg_token> [--name <alias>]"
  exit 1
}

URL="" TOKEN="" NAME=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --url)   URL="$2"; shift 2;;
    --token) TOKEN="$2"; shift 2;;
    --name)  NAME="$2"; shift 2;;
    *) usage;;
  esac
done
[[ -n "$URL" && -n "$TOKEN" ]] || usage

# Derive a normalized default name if none given:
if [[ -z "$NAME" ]]; then
  slug="${URL#https://github.com/}"
  slug="${slug//\//_}"
  NAME="$(echo "$slug" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_]/_/g')"
fi

CONFIG_ROOT=/home/runner/configs
BASE_RUNNER=/home/runner/base-runner
RUN_DIR="$CONFIG_ROOT/$NAME"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "[add-runner] Initializing directory for '$NAME'…"
  mkdir -p "$RUN_DIR"

  # Copy the runner bits
  cp -R "$BASE_RUNNER/." "$RUN_DIR"

  # Persist metadata
  printf "%s\n" "$URL"   > "$RUN_DIR/.url"
  printf "%s\n" "$TOKEN" > "$RUN_DIR/.token"

  # Fix permissions so runner user (UID 1000) can write
  chown -R 1000:1000 "$RUN_DIR"
fi

# Skip if the container already exists
if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "▶ Runner '$NAME' already exists. To redeploy, run: docker rm -f $NAME && add-runner …"
  exit 0
fi

echo "[add-runner] Spawning runner container '$NAME'…"
docker run -d \
  --name "$NAME" \
  -e RUNNER_NAME="$NAME" \
  -e RUNNER_REPO_URL="$URL" \
  -e RUNNER_TOKEN="$TOKEN" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$RUN_DIR":/opt/runner-files \
  ubuntu-runner

echo "[add-runner] ✅ Launched runner '$NAME'. Logs: docker logs -f $NAME"
```

### Docker Compose

```yaml
version: "3.8"
services:
  gh-multi-runner:
    build: .
    privileged: true
    security_opt:
      - seccomp:unconfined
    volumes:
      - ./configs:/home/runner/configs
      - type: tmpfs
        target: /var/lib/docker
      - type: tmpfs
        target: /run
    environment:
      - DOCKER_TLS_CERTDIR=
      - GH_RUNNER_VERSION=2.325.0
    restart: unless-stopped
```

## Example Usage

Build the supervisor container and spin it up, then add a runner using a GitHub registration token:

```bash
docker compose up -d --build
docker compose exec gh-multi-runner add-runner \
  --url https://github.com/arran4/goa4web \
  --token AAA3IMZJPA7QKYUIFN5SHKDINDWQ4
docker logs -f arran4_goa4web
```

### Rebuilding the supervisor

When you rebuild the `gh-multi-runner` service the supervisor will automatically re-launch every runner found under `configs/`. Directory names are normalised and if `.url` and `.token` exist they are passed to `docker run` so the container can reconfigure itself. Simply run:

```bash
docker compose up -d --build
```

All previously-added runners come back online without manual intervention. This setup lets you spawn as many runners as you need within a single DinD environment while keeping updates and configuration management streamlined.
