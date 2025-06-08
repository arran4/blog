---
title: "Deploying Sieve with JMAP"
date: 2025-06-08T17:05:00+10:00
draft: false
tags: ["sieve", "jmap", "stalwart"]
categories: ["tutorial"]
---

When running an email server you often want rules that sort incoming mail into
folders or handle it automatically.  The standard way to do this on the server
is with *Sieve* scripts.  Sieve is a simple language defined in RFC 5228 for
mail filtering.  It lets you match on message headers or other properties and
then file, forward or discard mail without needing any user client online.

Keeping such a script in version control makes it easy to track changes and to
reuse the same rules across servers.  In my case I'm deploying to the
[Stalwart](https://stalw.art/) mail server.  Because Stalwart exposes JMAP for
script management I can automate the upload directly from GitHub Actions.

Below is the workflow that I use.  Whenever I push `stalwart.sieve` to the `main`
branch, GitHub Actions authenticates against Stalwart's JMAP endpoint, uploads
the script and activates it.

```yaml
name: Deploy to Stalwart
on:
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
          curl -X POST -k -u "$STALWART_USER:$STALWART_PASS" \
            -H "Content-Type: application/json" \
            -d "$list_body" "$jmap_endpoint" | jq

          set_body=$(jq -n --arg accountId "$account_id" --arg blob "$blob_id" '{
            "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:sieve"],
            "methodCalls": [["SieveScript/set", {
              "accountId": $accountId,
              "create": {"A": {"name": "stalwart.sieve", "blobId": $blob}},
              "onSuccessActivateScript": "#A"
            }, "0"]]
          }')
          curl -X POST -k -u "$STALWART_USER:$STALWART_PASS" \
            -H "Content-Type: application/json" \
            -d "$set_body" "$jmap_endpoint" | jq
```

The script uses the [JMAP](https://www.rfc-editor.org/rfc/rfc8621) protocol to
upload the file and then activate it.  JMAP is JSON based and works nicely for
automation without having to open additional ports on the server.

You might use something like this when running in an environment with limited
network access where direct deployment isn't convenient.  Services such as
Codex which execute in a restricted container can still update your running
server via JMAP over HTTPS.  By keeping the Sieve rules in your repo you also
get history and the ability to review changes before deployment.

With the workflow above in place you just commit updates to `stalwart.sieve` and
push them to GitHub.  The action will deploy the new filter rules and activate
them automatically on your Stalwart server.

*This post was written with the assistance of an AI tool.*
