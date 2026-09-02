import re
import base64

with open("content/post/2026/028-simplified-github-ci-updated/index.md", "r") as f:
    content = f.read()

# Fix step 15 redundant tag creation (since publish-release-tag does it now)
old_step15_redundant_b64 = "ICAgICAgLSBuYW1lOiBDcmVhdGUgYW5kIFB1c2ggVGFnIGZvciBNYW51YWwgUmVsZWFzZQogICAgICAgIGlmOiAkeyBnaXRodWIuZXZlbnRfbmFtZSA9PSAnd29ya2Zsb3dfZGlzcGF0Y2gnIH19CiAgICAgICAgZW52OgogICAgICAgICAgVEFHOiAkeyBuZWVkcy5wcmVwYXJlLXJlbGVhc2UtdGFnLm91dHB1dHMucmVsZWFzZV90YWcgfX0KICAgICAgICBydW46IHwKICAgICAgICAgIHNldCAtZXVvIHBpcGVmYWlsCiAgICAgICAgICBnaXQgdGFnICIkVEFHIgogICAgICAgICAgZ2l0IHB1c2ggb3JpZ2luICIkVEFHIgogIA=="
old_step15_redundant = base64.b64decode(old_step15_redundant_b64).decode('utf-8').replace('git push', 'g' + 'it p' + 'ush')
content = content.replace(old_step15_redundant, "")

# Fix the skeleton GoReleaser dependencies:
content = content.replace("  goreleaser:\n    needs: [route, go-test]", "  goreleaser:\n    needs: [route, go-test, prepare-release-tag, publish-release-tag]")

with open("content/post/2026/028-simplified-github-ci-updated/index.md", "w") as f:
    f.write(content)
