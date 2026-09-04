import sys, re

def process_file(filename):
    with open(filename, "r") as f:
        content = f.read()

    if filename == "content/post/2026/042-simplified-github-ci-release-safe/index.md":

        new_validation = """## Step 7: release validation gate

To ensure a release is only created if the required validation passes, introduce a strict aggregation gate. Do not use a broad `always()` that might mask failures; explicitly require `success` for paths that discovery says are applicable.

```yaml
  release-validation:
    name: Release Validation Gate
    needs: [route, discover, go-checks]
    if: |
      always() &&
      needs.route.result == 'success' &&
      needs.discover.result == 'success' &&
      (needs.discover.outputs.has_go != 'true' || needs.go-checks.result == 'success')
    runs-on: ubuntu-latest
    steps:
      - run: echo "All required language checks passed."
```

---

## Step 8:"""
        content = content.replace("## Step 8:", new_validation)

        # Update step numbers... actually, adding a step means I have to renumber everything!
        # Instead of a new step, let's inject it into Step 7: "language lanes".
        # Let's see what is currently Step 7.
        pass

process_file("content/post/2026/042-simplified-github-ci-release-safe/index.md")
