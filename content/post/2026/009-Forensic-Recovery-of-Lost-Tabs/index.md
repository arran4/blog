---
title: "When Firefox Fails You: Forensic Recovery of Lost Tabs on Linux"
date: 2026-04-06T12:28:25+10:00
draft: false
tags: ["linux", "firefox", "recovery", "jsonlz4", "python"]
categories: ["tutorial", "forensics"]
---

### 1. Introduction

I recently lost a Firefox window during shutdown, and unfortunately, it was not saved in the session restore. It was a window filled with extensive research, consisting of many tabs meticulously grouped. Losing it meant losing a significant amount of context and work.

### 2. Initial Attempts (and why they failed)

My first instinct was to use standard Firefox features. I checked "Restore Previous Session" and "Recently Closed Windows," but the window simply was not there. Firefox had completely missed it during the shutdown sequence. These built-in features rely on the session state correctly persisting to disk during closure, which clearly had failed in my case.

### 3. Discovering Firefox Session Backups

Knowing that browsers maintain robust session states, I decided to dig into my profile directory to look for backups. On Linux, Firefox stores session data in:

```bash
~/.mozilla/firefox/<profile>/sessionstore-backups/
```

In this directory, you will typically find several files:
- `recovery.jsonlz4`
- `recovery.baklz4`
- `previous.jsonlz4`
- `upgrade.jsonlz4-*`

These files serve specific purposes:
- **recovery** represents the current state right before a crash.
- **recovery.bak** is a previous snapshot of the state.
- **previous** is the state from the last clean shutdown.

### 4. The `jsonlz4` Gotcha

My initial thought was to simply decompress these files. However, there is a significant gotcha: these are **not standard LZ4 files**. They contain a custom `mozLz40\0` magic header. If you try to use the standard `lz4` command line tool to decompress them, it will fail:

```bash
lz4 -d recovery.jsonlz4 recovery.json
```
```text
Error 44 : Unrecognized header
```

### 5. Decoding the Files Properly

To read these files, we need to bypass the custom header and decompress the raw LZ4 block. You can achieve this using Python. First, install the necessary Python bindings. On Gentoo, for example, you can emerge it:

```bash
sudo emerge --oneshot dev-python/lz4
```

Then, you can use the following Python snippet to properly decode the file:

```python
import lz4.block
from pathlib import Path

data = Path("recovery.jsonlz4").read_bytes()
# Skip the first 8 bytes containing the mozLz40\0 header
out = lz4.block.decompress(data[8:])
Path("recovery.json").write_bytes(out)
```

By skipping the first 8 bytes, we extract the raw LZ4 block rather than an LZ4 frame, allowing the standard block decompression to succeed.

### 6. Extracting Useful Data

Once decoded, `recovery.json` reveals the complex session structure. The primary path to your tabs is:
`windows -> tabs -> entries`

To find the most recent URL and title for each tab, you must select the entry corresponding to the `index` property of the tab object. The entries array contains the history of that specific tab, and the current state is tracked by this index.

### 7. Converting to Markdown

To make the recovered session useful, my goal was to turn the raw JSON into human-readable Markdown. Here is a simplified approach to generate a Markdown outline of the session:

```python
import json
from pathlib import Path

data = json.loads(Path("recovery.json").read_text())

for i, win in enumerate(data.get("windows", [])):
    print(f"## Window {i + 1}\n")
    for tab in win.get("tabs", []):
        entries = tab.get("entries", [])
        index = tab.get("index", 1) - 1
        if 0 <= index < len(entries):
            entry = entries[index]
            title = entry.get("title", "No Title")
            url = entry.get("url", "No URL")

            # Basic fallback for tab groups depending on version
            group = tab.get("groupId") or tab.get("extData", {}).get("group") or "Ungrouped"

            print(f"- **Group: {group}**")
            print(f"  - [{title}]({url})\n")
```

This script produces output similar to:

```markdown
## Window 1

- **Group: Docs**
  - [Page](url)

- **Group: Ungrouped**
  - [Title](url)
```

Handling tab groups can be tricky because the storage format is non-standard and varies by Firefox version or installed extensions. You might need to look for keys like `groupId`, `extData`, or `attributes` depending on your setup.

### 8. Results

After decoding and inspecting the files, the results were disappointing. The lost window was **not present** in `recovery`, `recovery.bak`, or `previous`.

Furthermore, I observed identical decoded sizes for both `recovery` and `recovery.bak`. This indicates that no new state was captured during the time the lost window was open. The conclusion is that Firefox never persisted that window to disk; it existed entirely in memory at the time of shutdown.

### 9. What Still Worked

Although the window's structured session was gone, the individual pages were not completely lost. The Firefox history database (`places.sqlite`) still contained the URLs I had visited. You can query this database directly to salvage links:

```bash
sqlite3 ~/.mozilla/firefox/<profile>/places.sqlite \
  "SELECT url, title FROM moz_places ORDER BY last_visit_date DESC LIMIT 50;"
```

### 10. Lessons Learned

This experience highlighted several important lessons about browser sessions:
- Firefox session persistence is not atomic.
- Shutdown timing matters significantly; a rapid or forced shutdown might prevent the final session state from being written.
- `recovery.baklz4` is often the best candidate for recovery since it might capture a state before a catastrophic failure or premature shutdown.
- Always check multiple backup files.
- Session files are entirely recoverable with the right tools, despite the custom header.
- Consider periodic tab or session exporters for critical work.

### 11. Optional Improvements

To prevent this from happening again, there are a few strategies you can employ:
- Set up a cron job to snapshot the `sessionstore-backups` directory periodically.
- Install browser extensions dedicated to reliable tab export and session management.
- Utilize filesystem-level snapshots (like btrfs or ZFS) for your home directory to easily roll back to a known good state.
