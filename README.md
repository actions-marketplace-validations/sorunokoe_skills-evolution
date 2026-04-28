<div align="center">

# skills-evolution

**Keep your AI skill files accurate, up to date, and evolving — automatically.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)

[For teams](#quick-start--teams) · [For OSS skill maintainers](#for-oss-skill-maintainers) · [What it does](#what-it-does) · [Reference](#reference) · [Showcase](#showcase)

</div>

---

AI skill governance for software teams using `.github/skills/` or `.claude/skills/` guidance files.

**Every month:** discover library versions → detect stale advice → patch outdated content → open a PR.  
**Every PR touching a skill:** post a concise AI review comment.

---

## What it does

| Feature | Description |
|---|---|
| **PR review** | On every PR touching a skill file, posts a concise AI review covering accuracy, scope, and anti-patterns |
| **Version tracking** | Discovers library versions from `Package.resolved`, `go.mod`, `Cargo.lock`, `pubspec.yaml`, `package.json` |
| **AI content update** | Calls GitHub Models once per skill file — patches version references, opens a PR |
| **Structural audit** | Checks frontmatter fields and broken local links — auto-fixes where safe |
| **OSS mode** | Governs standalone skill repos where `SKILL.md` lives at the repo root |
| **Path safety** | Only patches files inside `*/skills/*/` — never arbitrary files |

Skill files are discovered from:
- `.github/skills/<name>/SKILL.md` — Copilot, Xcode, and other GitHub-aware agents
- `.claude/skills/<name>/SKILL.md` — Claude-specific skills

---

## Quick start — teams

### Option A: gh-aw (recommended, ~30 seconds)

```bash
# Review skill files on every PR that changes them
gh aw add sorunokoe/skills-evolution/workflows/skills-pr-check.md@latest
gh aw compile

# Auto-update skill content on a schedule (default: monthly)
gh aw add sorunokoe/skills-evolution/workflows/skills-monthly-update.md@latest
gh aw compile
```

No Python, no YAML to maintain. Run on demand: `gh aw run skills-monthly-update`.

> **Changing the schedule:** Edit `schedule:` in `.github/workflows/skills-monthly-update.md`
> (e.g. `schedule: weekly`), then `gh aw compile`.

### Option B: GitHub Actions

<details>
<summary><strong>PR skill review</strong></summary>

```yaml
# .github/workflows/skills-pr-check.yml
name: Skills PR Check
on:
  pull_request:
    paths: [".github/skills/**", ".claude/skills/**"]
permissions:
  contents: read
  pull-requests: write
jobs:
  check:
    uses: sorunokoe/skills-evolution/.github/workflows/skills_pr_check.yml@latest
    with:
      tech_stack: ""   # optional: e.g. "Swift, KMP, SwiftUI"
    secrets:
      copilot_token: ${{ secrets.COPILOT_TOKEN }}
```
</details>

<details>
<summary><strong>Monthly skill update</strong></summary>

```yaml
# .github/workflows/skills-health.yml
name: Skills Health
on:
  schedule:
    - cron: "0 3 1 * *"   # monthly — change to any schedule you like
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
  models: read
jobs:
  health:
    uses: sorunokoe/skills-evolution/.github/workflows/skills-health.yml@latest
    with:
      enable_ai_skill_update: true
    secrets:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```
</details>

---

## For OSS skill maintainers

Publishing a standalone AI skill repo (like [swift-kmp-skill](https://github.com/sorunokoe/swift-kmp-skill))?  
Use **OSS mode** — it expects `SKILL.md` at the repo root and `references/*.md` as skill content.

### Setup

```bash
# PR review — triggers on every PR touching SKILL.md or references/**
gh aw add sorunokoe/skills-evolution/workflows/oss-skill-pr-check.md@latest

# Monthly update — version checks, AI patches, opens PR
gh aw add sorunokoe/skills-evolution/workflows/oss-skill-update.md@latest

gh aw compile
```

Or with GitHub Actions:

<details>
<summary><strong>GitHub Actions workflow</strong></summary>

```yaml
# .github/workflows/skill-health.yml
name: Skill Health
on:
  schedule:
    - cron: "0 3 1 * *"
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
  models: read
jobs:
  health:
    uses: sorunokoe/skills-evolution/.github/workflows/oss-skill-health.yml@latest
    with:
      enable_ai_skill_update: true
    secrets:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```
</details>

### OSS vs default mode

| | Default (team repo) | OSS (skill repo) |
|--|---|---|
| Skill files discovered | `.github/skills/*/SKILL.md` | `SKILL.md` at root |
| Markdown audited | All `*.md` under skill dir | `SKILL.md` + `references/*.md` only |
| Skill identity | Folder name | `name:` from frontmatter |
| Name/folder mismatch | ✅ checked | ❌ skipped (CI checkout dir is arbitrary) |
| Registry drift | ✅ checked | ❌ skipped |
| Feedback collection | ✅ | ❌ (OSS PRs are maintainer edits) |
| Missing `SKILL.md` | Silent | Error finding emitted |

---

## Reference

<details>
<summary><strong>Python package</strong></summary>

```bash
pip install skills-evolution
```

Entry points: `skills-evolution`, `skills-evolution-health`, `skills-evolution-ai-update`, `skills-evolution-mcp`, `skills-evolution-semantic-pass`.

Run from source:

```bash
PYTHONPATH=src python3 -m skills_evolution.cli --help
PYTHONPATH=src python3 -m skills_evolution.health --help
```
</details>

<details>
<summary><strong>Trace CLI</strong></summary>

Record which skill sections an agent used while solving a task:

```bash
skills-evolution write \
  --repo-root /path/to/repo \
  --skill swiftui-standards \
  --file .github/skills/swiftui-standards/references/state-management.md \
  --section-id tca-store-ownership \
  --line-start 1 --line-end 34 \
  --reason "Used ownership rule for StoreOf wrapper choice" \
  --confidence 0.86

# Publish traces to the current branch PR
skills-evolution publish --repo-root /path/to/repo
```
</details>

<details>
<summary><strong>Health toolkit CLI</strong></summary>

```bash
# Structural audit
skills-evolution-health audit --repo-root . --output-dir outputs

# Collect PR feedback signals
skills-evolution-health collect-feedback \
  --repo owner/repo --token "$GH_TOKEN" --output outputs/raw.json

# Analyze feedback into proposals
skills-evolution-health feedback \
  --repo-root . --raw outputs/raw.json --output-dir outputs

# Combine all reports into a summary
skills-evolution-health combine --output-dir outputs
```
</details>

<details>
<summary><strong>MCP server</strong></summary>

```bash
skills-evolution-mcp
```

Exposes: `record_skill_trace`, `publish_skill_traces_to_pr`.
</details>

<details>
<summary><strong>Optional AI semantic pass</strong></summary>

```bash
skills-evolution-semantic-pass \
  --repo-root . \
  --output-dir outputs \
  --copilot-token "$COPILOT_TOKEN"
```
</details>

---

## Showcase

Open-source AI skill repos governed by skills-evolution:

| Skill | What it covers | Repo |
|-------|---------------|------|
| **swift-kmp** | KMP ↔ Swift bridge patterns — interactors, `SkieSwiftFlow` → `AsyncStream`, type mapping, `KotlinThrowable` containment | [sorunokoe/swift-kmp-skill](https://github.com/sorunokoe/swift-kmp-skill) |
| **swiftui-compose** | Bidirectional Compose Multiplatform ↔ SwiftUI interop — `UIViewControllerRepresentable`, coordinator, state sharing | [sorunokoe/swiftui-compose-skill](https://github.com/sorunokoe/swiftui-compose-skill) |

> Maintaining an open-source skill? Add the `maintained by skills-evolution` badge and the OSS workflows — see [For OSS skill maintainers](#for-oss-skill-maintainers) above.

---

## Contributing

Open an issue or pull request. Tests live in `tests/` — run with `python3 -m pytest tests/`.

## License

[MIT](LICENSE)
