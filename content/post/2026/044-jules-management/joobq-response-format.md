# Joobq reply-format rule for the Jules management guide

The following section is intended to be incorporated into `index.md` under its existing joobq / out-of-band question guidance. The joobq answer is relayed manually by the human into the Jules interface, rather than posted as a GitHub comment.

## Mandatory format for a joobq reply

When the human presents a `joobq` / Jules out-of-band question, **always provide the complete, ready-to-paste reply in a single plain fenced code block** (prefer `text`), not a writing block, interactive component, quotation, or formatted prose that the human must reconstruct. The copyable code block is the default even if the human did not explicitly request it. The human should be able to select or copy the entire message verbatim and paste it into the Jules question field.

Put any necessary context, assessment, or GitHub references outside the code block and keep the instructions to Jules wholly inside it. Do not make the user assemble a message from multiple snippets or substitute a GitHub comment for the out-of-band response. Avoid `@jules` mentions in the out-of-band message: those belong in GitHub comments, not in the Jules interface. Include the actionable answer, specific next steps, required verification and the requested PR submission or follow-up where applicable. Preserve the assigned Jules task/branch model; do not direct a running Jules task to switch, reset, rebase, or create another branch.

When a live PR exists and the user **also** explicitly asks for a GitHub comment, perform that separate action through GitHub and still provide the standalone copyable joobq reply. When the prompt is a joobq without a PR, do **not** invent a PR URL or say that the user can reply on GitHub.

Do not use a `WritingBlock` or other rich editor for the joobq response: the relaying surface is a plain-text Jules input, and a fenced code block must be supplied for reliable copy/paste.
