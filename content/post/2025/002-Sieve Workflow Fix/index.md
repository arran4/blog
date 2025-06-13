---
title: "Update to Sieve Deployment Workflow"
date: 2025-06-09T10:00:00+10:00
draft: false
tags: ["sieve", "jmap", "stalwart"]
categories: ["tutorial"]
---

In the previous post on deploying Sieve filters to Stalwart using JMAP the workflow always created a new script. After some testing I realised it should update the existing script when one already exists. Below is the corrected workflow.

```yaml
name: Deploy to Stalwart
"on":
  push:
    paths:
      - 'stalwart.sieve'
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install tools
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
      - name: Upload via JMAP
        env:
          STALWART_JMAP_URL: ${{ vars.STALWART_JMAP_URL }}
          STALWART_USER: ${{ secrets.STALWART_USER }}
          STALWART_PASS: ${{ secrets.STALWART_PASS }}
        run: |
          set -e
          set -x
          base_url="${STALWART_JMAP_URL%/jmap*}"
          session_json=$(curl -X GET -k -u "$STALWART_USER:$STALWART_PASS" "$base_url/.well-known/jmap")
          account_id=$(echo "$session_json" | jq -r '.primaryAccounts["urn:ietf:params:jmap:sieve"]')

          jmap_endpoint="${STALWART_JMAP_URL%/}"
          upload_url="${jmap_endpoint}/upload/${account_id}"

          curl -X POST -k -u "$STALWART_USER:$STALWART_PASS" \
            -H "Content-Type: application/sieve" \
            --data-binary @stalwart.sieve "$upload_url" > upload.json
          blob_id=$(jq -r '.blobId' upload.json)
          if [ "$blob_id" = "null" ] || [ -z "$blob_id" ]; then
            echo "Upload failed" >&2
            cat upload.json
            exit 1
          fi

          list_body=$(jq -n --arg accountId "$account_id" '{
            "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:sieve"],
            "methodCalls": [["SieveScript/get", {"accountId": $accountId}, "0"]]
          }')
          list_resp=$(curl -X POST -k -u "$STALWART_USER:$STALWART_PASS" \
            -H "Content-Type: application/json" \
            -d "$list_body" "$jmap_endpoint")
          echo "$list_resp" | jq
          existing_id=$(echo "$list_resp" | jq -r '.methodResponses[0][1].list[] | select(.name=="stalwart.sieve") | .id')

          if [ -n "$existing_id" ] && [ "$existing_id" != "null" ]; then
            set_body=$(jq -n --arg accountId "$account_id" --arg blob "$blob_id" --arg id "$existing_id" '{
              "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:sieve"],
              "methodCalls": [["SieveScript/set", {
                "accountId": $accountId,
                "update": {($id): {"blobId": $blob}},
                "onSuccessActivateScript": $id
              }, "0"]]
            }')
          else
            set_body=$(jq -n --arg accountId "$account_id" --arg blob "$blob_id" '{
              "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:sieve"],
              "methodCalls": [["SieveScript/set", {
                "accountId": $accountId,
                "create": {"A": {"name": "stalwart.sieve", "blobId": $blob}},
                "onSuccessActivateScript": "#A"
              }, "0"]]
            }')
          fi
          curl -X POST -k -u "$STALWART_USER:$STALWART_PASS" \
            -H "Content-Type: application/json" \
            -d "$set_body" "$jmap_endpoint" | jq
```

This version first queries existing scripts and either updates the current one or creates it if missing.

*This post was written with the assistance of an AI tool.*
