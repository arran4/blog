import re

def fix_042():
    with open('content/post/2026/042-simplified-github-ci-release-safe/index.md', 'r') as f:
        content = f.read()

    # 1. Update publisher conditions in Step 11
    # We need to change conditions for goreleaser and github-release to require startsWith(github.ref, 'refs/tags/')
    # Let's find the current conditions.

    # goreleaser
    content = re.sub(
        r'(goreleaser:\n\s+name: Publish Go artifacts\n\s+needs: \[.*\]\n\s+if: \$\{\{ !failure\(\) && !cancelled\(\) && needs\.route\.outputs\.run_release == \'true\' && needs\.detect\.outputs\.has_go == \'true\') (\}\})',
        r"\1 && startsWith(github.ref, 'refs/tags/') \2",
        content
    )

    # github-release
    content = re.sub(
        r'(github-release:\n\s+name: Publish release\n\s+needs: \[.*\]\n\s+if: \$\{\{ !failure\(\) && !cancelled\(\) && needs\.route\.outputs\.run_release == \'true\') (\}\})',
        r"\1 && startsWith(github.ref, 'refs/tags/') \2",
        content
    )


    # 2. Finish the shell-injection cleanup in 042 (Step 4, and other router uses)

    # Step 4: MODE="${{ inputs.mode }}" -> MODE="$INPUT_MODE"
    content = re.sub(
        r'          MODE="\$\{\{ inputs\.mode \}\}"\n',
        r'          MODE="$INPUT_MODE"\n',
        content
    )

    # Router uses in 042:

    content = re.sub(
        r'          if \[\[ "\$\{\{ github\.event\.action \}\}" == "closed" && "\$\{\{ github\.event\.pull_request\.merged \}\}" == "true" \]\]; then\n',
        r'          if [[ "$EVENT_ACTION" == "closed" && "$PR_MERGED" == "true" ]]; then\n',
        content
    )

    content = re.sub(
        r'          if \[\[ "\$\{\{ github\.event_name \}\}" == "schedule" && "\$\{\{ github\.event\.schedule \}\}" == "0 19 1 \* \*" \]\]; then\n',
        r'          if [[ "$EVENT_NAME" == "schedule" && "$EVENT_SCHEDULE" == "0 19 1 * *" ]]; then\n',
        content
    )

    content = re.sub(
        r'          if \[\[ "\$\{\{ github\.event_name \}\}" == "schedule" && "\$\{\{ github\.event\.schedule \}\}" == "41 2 \* \* \*" \]\]; then\n',
        r'          if [[ "$EVENT_NAME" == "schedule" && "$EVENT_SCHEDULE" == "41 2 * * *" ]]; then\n',
        content
    )

    content = re.sub(
        r'              if \[\[ "\$\{\{ github\.ref \}\}" == refs/tags/\*test\* \]\]; then\n',
        r'              if [[ "$REF" == refs/tags/*test* ]]; then\n',
        content
    )

    content = re.sub(
        r'              if \[\[ "\$\{\{ github\.ref \}\}" == refs/tags/\*test\* \]\]; then\n',
        r'              if [[ "$REF" == refs/tags/*test* ]]; then\n',
        content
    )

    content = re.sub(
        r'              if \[\[ "\$\{\{ inputs\.mode \}\}" == "test" \]\]; then\n',
        r'              if [[ "$INPUT_MODE" == "test" ]]; then\n',
        content
    )

    # Update env block for route step
    content = re.sub(
        r'      - id: route\n        shell: bash\n        env:\n          EVENT_NAME: \$\{\{ github\.event_name \}\}\n          REF: \$\{\{ github\.ref \}\}\n        run: \|\n',
        r'      - id: route\n        shell: bash\n        env:\n          EVENT_NAME: ${{ github.event_name }}\n          REF: ${{ github.ref }}\n          EVENT_ACTION: ${{ github.event.action }}\n          PR_MERGED: ${{ github.event.pull_request.merged }}\n          INPUT_MODE: ${{ inputs.mode }}\n          EVENT_SCHEDULE: ${{ github.event.schedule }}\n        run: |\n',
        content
    )

    # Any remaining?
    # Let's check `inputs.mode` in tag step.
    content = re.sub(
        r'          if \[\[ "\$\{\{ inputs\.mode \}\}" == "publish-tag" \]\]; then\n',
        r'          if [[ "$INPUT_MODE" == "publish-tag" ]]; then\n',
        content
    )

    content = re.sub(
        r'          if \[\[ "\$\{\{ inputs\.mode \}\}" == "test" \]\]; then\n',
        r'          if [[ "$INPUT_MODE" == "test" ]]; then\n',
        content
    )

    # add INPUT_MODE to env of tag step if not already there
    if 'INPUT_MODE: ${{ inputs.mode }}' not in content[content.find('      - id: tag\n'):]:
        content = re.sub(
            r'      - id: tag\n        shell: bash\n        env:\n          EVENT_NAME: \$\{\{ github\.event_name \}\}\n          REF_NAME: \$\{\{ github\.ref_name \}\}\n          INPUT_RELEASE_VERSION_OVERRIDE: \$\{\{ inputs\.release_version_override \}\}\n        run: \|\n',
            r'      - id: tag\n        shell: bash\n        env:\n          EVENT_NAME: ${{ github.event_name }}\n          REF_NAME: ${{ github.ref_name }}\n          INPUT_RELEASE_VERSION_OVERRIDE: ${{ inputs.release_version_override }}\n          INPUT_MODE: ${{ inputs.mode }}\n        run: |\n',
            content
        )

    with open('content/post/2026/042-simplified-github-ci-release-safe/index.md', 'w') as f:
        f.write(content)

def fix_041():
    pass
    # We already fixed 041, but let's just make sure there are no remaining ${{ ... }} in run: blocks
    with open('content/post/2026/041-release-safe-single-owner-github-ci/index.md', 'r') as f:
        content = f.read()

    with open('content/post/2026/041-release-safe-single-owner-github-ci/index.md', 'w') as f:
        f.write(content)

fix_042()
fix_041()
