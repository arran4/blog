---
title: "Fixing Docker Permissions in the Self-Hosted Runner Image"
date: 2025-07-08T20:26:26+10:00
draft: false
tags: ["github-actions", "docker", "devops"]
categories: ["devops"]
author: "Arran Ubels"
---

While testing the multi-runner setup I discovered containers started by the `runner` user could not invoke Docker. The base image lacked the `docker.io` package and the user was missing membership of the `docker` group.

The `Dockerfile.ubuntu-runner` now installs Docker and ensures the `runner` user belongs to the `docker` group so each containerised runner can start sibling containers without needing root:

```diff
@@
-RUN apt-get update && apt-get install -y \
-      curl git jq sudo nodejs npm \
-      libicu70 libssl-dev libcurl4-openssl-dev \
+RUN apt-get update && apt-get install -y \
+      curl git jq sudo nodejs npm \
+      libicu70 libssl-dev libcurl4-openssl-dev \
+      docker.io \
     && rm -rf /var/lib/apt/lists/*
@@
-RUN useradd -m -s /bin/bash runner
+RUN useradd -m -s /bin/bash runner && usermod -a -G docker runner
```

With these tweaks the runner containers can spin up jobs that use Docker without permission errors.
