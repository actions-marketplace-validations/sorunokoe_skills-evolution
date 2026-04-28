from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skills_evolution import health


class HealthTests(unittest.TestCase):
	def test_combine_reports_without_semantic_file_stays_honest(self) -> None:
		with tempfile.TemporaryDirectory() as tmp_dir:
			output_dir = Path(tmp_dir)
			(output_dir / "skills-audit.json").write_text(json.dumps({"findings_count": 2}), encoding="utf-8")
			(output_dir / "skills-feedback.json").write_text(
				json.dumps(
					{
						"proposal_count": 1,
						"trace_count": 3,
						"comment_signal_count": 0,
						"disputed_sections": [{"skill": "swiftui-standards"}],
					}
				),
				encoding="utf-8",
			)

			findings, proposals = health.combine_reports(output_dir)

			self.assertEqual(findings, 2)
			self.assertEqual(proposals, 1)
			summary = (output_dir / "skills-health-summary.md").read_text(encoding="utf-8")
			self.assertIn("2 structural issue(s)", summary)
			self.assertIn("skills-audit.md", summary)

	def test_combine_reports_with_ai_updates_increments_findings(self) -> None:
		with tempfile.TemporaryDirectory() as tmp_dir:
			output_dir = Path(tmp_dir)
			(output_dir / "skills-audit.json").write_text(json.dumps({"findings_count": 0}), encoding="utf-8")
			(output_dir / "skills-feedback.json").write_text(
				json.dumps({"proposal_count": 0, "trace_count": 0, "comment_signal_count": 0, "disputed_sections": []}),
				encoding="utf-8",
			)
			(output_dir / "skills-ai-updates.json").write_text(
				json.dumps({
					"total_patches_applied": 3,
					"skills_changed": 2,
					"skills_processed": 5,
					"total_patches_skipped": 1,
					"total_patches_ambiguous": 0,
					"by_skill": [
						{"skill": "tca-standards", "applied": 2, "summary": "Updated TCA version."},
						{"skill": "swiftui-standards", "applied": 1, "summary": "Updated SwiftUI API."},
					],
				}),
				encoding="utf-8",
			)

			findings, proposals = health.combine_reports(output_dir)

			# AI patches applied (3) should be folded into findings_count.
			self.assertEqual(findings, 3)
			summary = (output_dir / "skills-health-summary.md").read_text(encoding="utf-8")
			self.assertIn("3 version patches", summary)
			self.assertIn("tca-standards", summary)
			self.assertIn("swiftui-standards", summary)

	def test_analyze_feedback_uses_normal_review_comments(self) -> None:
		with tempfile.TemporaryDirectory() as tmp_dir:
			repo_root = Path(tmp_dir) / "repo"
			skill_dir = repo_root / ".github" / "skills" / "swiftui-standards"
			skill_dir.mkdir(parents=True)
			(skill_dir / "SKILL.md").write_text(
				"---\nname: swiftui-standards\ndescription: SwiftUI guidance\napplyTo: '**/*.swift'\n---\n",
				encoding="utf-8",
			)
			raw_path = Path(tmp_dir) / "raw.json"
			raw_path.write_text(
				json.dumps(
					{
						"pull_requests": [
							{
								"number": 42,
								"body": "",
								"issue_comments": [
									{"body": "swiftui-standards should mention NavigationPath handling for deep links."},
									{"body": "SwiftUI standards needs guidance for path restoration."},
								],
								"review_comments": [],
								"reviews": [],
							}
						]
					}
				),
				encoding="utf-8",
			)
			output_dir = Path(tmp_dir) / "outputs"

			proposals = health.analyze_feedback(raw_path, repo_root, output_dir)

			self.assertEqual(proposals, 1)
			feedback = json.loads((output_dir / "skills-feedback.json").read_text(encoding="utf-8"))
			self.assertEqual(feedback["comment_signal_count"], 2)
			self.assertEqual(feedback["metrics_by_skill"]["swiftui-standards"]["comment_gap"], 2)
			self.assertEqual(feedback["proposal_count"], 1)
			report = (output_dir / "skills-feedback.md").read_text(encoding="utf-8")
			self.assertIn("Review comment signals analyzed: 2", report)
			self.assertIn("gap=2", report)


class OssSkillFilesTests(unittest.TestCase):
	def _make_oss_repo(self, tmp_dir: str, with_skill: bool = True, with_refs: bool = True) -> Path:
		repo_root = Path(tmp_dir) / "swift-kmp"
		repo_root.mkdir(parents=True)
		if with_skill:
			(repo_root / "SKILL.md").write_text(
				"---\nname: swift-kmp\ndescription: KMP bridge patterns\napplyTo: '**/*.swift'\n---\n",
				encoding="utf-8",
			)
			(repo_root / "README.md").write_text("# swift-kmp\n", encoding="utf-8")
		if with_refs:
			refs = repo_root / "references"
			refs.mkdir()
			(refs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
			(refs / "flow-bridging.md").write_text("# Flow\n", encoding="utf-8")
		return repo_root

	def test_iter_oss_skill_files_found(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = self._make_oss_repo(tmp)
			files = health.iter_oss_skill_files(repo_root)
			self.assertEqual(len(files), 1)
			self.assertEqual(files[0].name, "SKILL.md")
			self.assertEqual(files[0].parent, repo_root)

	def test_iter_oss_skill_files_missing(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = self._make_oss_repo(tmp, with_skill=False)
			files = health.iter_oss_skill_files(repo_root)
			self.assertEqual(files, [])

	def test_iter_oss_markdown_files_includes_skill_and_refs(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = self._make_oss_repo(tmp)
			files = health.iter_oss_markdown_files(repo_root)
			names = [f.name for f in files]
			self.assertIn("SKILL.md", names)
			self.assertIn("architecture.md", names)
			self.assertIn("flow-bridging.md", names)
			# README.md must not be included
			self.assertNotIn("README.md", names)

	def test_iter_oss_markdown_files_excludes_readme(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = self._make_oss_repo(tmp)
			files = health.iter_oss_markdown_files(repo_root)
			self.assertFalse(any(f.name == "README.md" for f in files))

	def test_iter_oss_markdown_files_without_refs_dir(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = self._make_oss_repo(tmp, with_refs=False)
			files = health.iter_oss_markdown_files(repo_root)
			self.assertEqual([f.name for f in files], ["SKILL.md"])


class OssAuditModeTests(unittest.TestCase):
	def _make_oss_repo(self, tmp_dir: str, skill_content: str | None = None) -> tuple[Path, Path]:
		repo_root = Path(tmp_dir) / "swift-kmp"
		repo_root.mkdir(parents=True)
		output_dir = Path(tmp_dir) / "output"
		output_dir.mkdir()
		if skill_content is not None:
			(repo_root / "SKILL.md").write_text(skill_content, encoding="utf-8")
		return repo_root, output_dir

	def test_audit_oss_missing_skill_md_emits_error(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root, output_dir = self._make_oss_repo(tmp, skill_content=None)
			findings_count = health.audit_skills(repo_root, output_dir, apply_autofix=False, oss=True)
			self.assertGreater(findings_count, 0)
			audit = json.loads((output_dir / "skills-audit.json").read_text(encoding="utf-8"))
			types = [f["type"] for f in audit["findings"]]
			self.assertIn("MISSING_SKILL_FILE", types)

	def test_audit_oss_valid_skill_no_findings(self) -> None:
		content = "---\nname: swift-kmp\ndescription: KMP bridge patterns\napplyTo: '**/*.swift'\n---\n"
		with tempfile.TemporaryDirectory() as tmp:
			repo_root, output_dir = self._make_oss_repo(tmp, skill_content=content)
			findings_count = health.audit_skills(repo_root, output_dir, apply_autofix=False, oss=True)
			self.assertEqual(findings_count, 0)

	def test_audit_oss_no_folder_mismatch_warning(self) -> None:
		# name in frontmatter is "swift-kmp" but checkout dir is "workspace" — must not warn
		content = "---\nname: swift-kmp\ndescription: KMP patterns\napplyTo: '**/*.swift'\n---\n"
		with tempfile.TemporaryDirectory() as tmp:
			# Use "workspace" as the checkout dir name to simulate CI
			repo_root = Path(tmp) / "workspace"
			repo_root.mkdir()
			output_dir = Path(tmp) / "output"
			output_dir.mkdir()
			(repo_root / "SKILL.md").write_text(content, encoding="utf-8")
			findings_count = health.audit_skills(repo_root, output_dir, apply_autofix=False, oss=True)
			self.assertEqual(findings_count, 0)
			audit = json.loads((output_dir / "skills-audit.json").read_text(encoding="utf-8"))
			types = [f["type"] for f in audit["findings"]]
			self.assertNotIn("METADATA_DRIFT", types)

	def test_audit_oss_no_registry_drift_check(self) -> None:
		content = "---\nname: swift-kmp\ndescription: KMP patterns\napplyTo: '**/*.swift'\n---\n"
		with tempfile.TemporaryDirectory() as tmp:
			repo_root, output_dir = self._make_oss_repo(tmp, skill_content=content)
			# Add a copilot-instructions.md that does NOT list the skill — in OSS mode
			# this should be completely ignored.
			gh = repo_root / ".github"
			gh.mkdir()
			(gh / "copilot-instructions.md").write_text("# Instructions\nNo skills table here.\n", encoding="utf-8")
			findings_count = health.audit_skills(repo_root, output_dir, apply_autofix=False, oss=True)
			self.assertEqual(findings_count, 0)
			audit = json.loads((output_dir / "skills-audit.json").read_text(encoding="utf-8"))
			types = [f["type"] for f in audit["findings"]]
			self.assertNotIn("REGISTRY_DRIFT", types)

	def test_audit_oss_uses_frontmatter_name_as_skill_label(self) -> None:
		# Incomplete frontmatter — name missing → finding should be labeled with fallback
		content = "---\ndescription: KMP patterns\napplyTo: '**/*.swift'\n---\n"
		with tempfile.TemporaryDirectory() as tmp:
			repo_root, output_dir = self._make_oss_repo(tmp, skill_content=content)
			findings_count = health.audit_skills(repo_root, output_dir, apply_autofix=False, oss=True)
			self.assertGreater(findings_count, 0)
			audit = json.loads((output_dir / "skills-audit.json").read_text(encoding="utf-8"))
			# skill label should be the repo dir name (fallback) since name: is missing
			self.assertTrue(any(f["skill"] for f in audit["findings"]))


class SkillQualityChecksTests(unittest.TestCase):
	"""Tests for SKILL_TOO_LONG, agent optimization, and contradiction detection."""

	def _make_valid_skill_content(self, extra: str = "") -> str:
		"""Minimal valid SKILL.md with routing section + code example."""
		return (
			"---\nname: my-skill\ndescription: test\napplyTo: '**/*.swift'\n---\n"
			"# My Skill\n\n## Reference Router\n\n| Task | File |\n|------|------|\n\n"
			"```swift\nfoo()\n```\n" + extra
		)

	# ── SKILL_TOO_LONG ──────────────────────────────────────────────────────

	def test_skill_too_long_emits_warning(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			skill_file.write_text("\n".join(["line"] * 301), encoding="utf-8")
			findings = health._check_skill_length(skill_file, root, "my-skill", 301)
			self.assertEqual(len(findings), 1)
			self.assertEqual(findings[0].type, "SKILL_TOO_LONG")
			self.assertEqual(findings[0].severity, "warning")

	def test_skill_within_limit_no_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			skill_file.write_text("\n".join(["line"] * 100), encoding="utf-8")
			findings = health._check_skill_length(skill_file, root, "my-skill", 100)
			self.assertEqual(findings, [])

	def test_skill_exactly_at_limit_no_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			skill_file.write_text("\n".join(["line"] * 300), encoding="utf-8")
			findings = health._check_skill_length(skill_file, root, "my-skill", 300)
			self.assertEqual(findings, [])

	# ── Agent optimization checks ───────────────────────────────────────────

	def test_stub_skill_skips_optimization_checks(self) -> None:
		"""Frontmatter-only files should not trigger NO_ROUTING_SECTION."""
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			content = "---\nname: my-skill\ndescription: test\napplyTo: '**/*.swift'\n---\n"
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			self.assertEqual(findings, [])

	def test_no_routing_section_emits_warning(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			content = "---\nname: my-skill\ndescription: test\napplyTo: '**/*.swift'\n---\n# My Skill\n\n❌ `BadAPI`\n\n```swift\nfoo()\n```\n"
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			types = {f.type for f in findings}
			self.assertIn("NO_ROUTING_SECTION", types)

	def test_routing_section_present_no_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			content = self._make_valid_skill_content()
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			types = {f.type for f in findings}
			self.assertNotIn("NO_ROUTING_SECTION", types)

	def test_rules_without_examples_emits_warning(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			# Has routing, has rules, but NO code fence
			content = "---\nname: my-skill\ndescription: x\napplyTo: '**'\n---\n# A\n\n## Reference Router\n\n❌ Never do X\n✅ Do Y\n"
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			types = {f.type for f in findings}
			self.assertIn("RULES_WITHOUT_EXAMPLES", types)

	def test_rules_with_examples_no_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			content = self._make_valid_skill_content("❌ Bad\n")
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			types = {f.type for f in findings}
			self.assertNotIn("RULES_WITHOUT_EXAMPLES", types)

	def test_deep_heading_nesting_emits_info(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			content = self._make_valid_skill_content("#### Deep section\n")
			skill_file.write_text(content, encoding="utf-8")
			findings = health._check_agent_optimization(skill_file, content, root, "my-skill")
			types = {f.type for f in findings}
			self.assertIn("DEEP_HEADING_NESTING", types)

	# ── Contradiction detection ─────────────────────────────────────────────

	def test_contradicting_rules_across_files_detected(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			file_a = root / "SKILL.md"
			file_b = root / "ref.md"
			file_a.write_text("# A\n\n❌ `SomeAPI` is forbidden\n", encoding="utf-8")
			file_b.write_text("# B\n\n✅ `SomeAPI` is recommended\n", encoding="utf-8")
			pairs = [(file_a, file_a.read_text()), (file_b, file_b.read_text())]
			findings = health._check_contradictions(pairs, root, "my-skill")
			self.assertEqual(len(findings), 1)
			self.assertEqual(findings[0].type, "CONTRADICTING_RULES")
			self.assertIn("someapi", findings[0].message)

	def test_no_contradiction_same_file_before_after(self) -> None:
		"""❌ then ✅ of the same term in one file is a before/after example, not a contradiction."""
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			skill_file = root / "SKILL.md"
			skill_file.write_text("# A\n\n❌ `SomeAPI` bad way\n✅ `SomeAPI` good way\n", encoding="utf-8")
			pairs = [(skill_file, skill_file.read_text())]
			findings = health._check_contradictions(pairs, root, "my-skill")
			self.assertEqual(findings, [])

	def test_no_contradiction_when_consistent(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			file_a = root / "SKILL.md"
			file_b = root / "ref.md"
			file_a.write_text("# A\n\n❌ `BadAPI`\n", encoding="utf-8")
			file_b.write_text("# B\n\n✅ `GoodAPI`\n", encoding="utf-8")
			pairs = [(file_a, file_a.read_text()), (file_b, file_b.read_text())]
			findings = health._check_contradictions(pairs, root, "my-skill")
			self.assertEqual(findings, [])

	def test_contradiction_inside_code_fence_ignored(self) -> None:
		"""❌/✅ inside fenced code blocks must not be treated as normative rules."""
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			file_a = root / "SKILL.md"
			file_b = root / "ref.md"
			# ❌ `SomeAPI` is INSIDE a code fence — should not count
			file_a.write_text("# A\n\n```\n// ❌ `SomeAPI` avoid this\n```\n", encoding="utf-8")
			file_b.write_text("# B\n\n✅ `SomeAPI` use this\n", encoding="utf-8")
			pairs = [(file_a, file_a.read_text()), (file_b, file_b.read_text())]
			findings = health._check_contradictions(pairs, root, "my-skill")
			self.assertEqual(findings, [])

	def test_one_finding_per_term_not_per_file_pair(self) -> None:
		"""Multiple files preferring a term that one file bans → single finding."""
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			file_a = root / "SKILL.md"
			file_b = root / "ref1.md"
			file_c = root / "ref2.md"
			file_a.write_text("# A\n\n❌ `SomeAPI`\n", encoding="utf-8")
			file_b.write_text("# B\n\n✅ `SomeAPI`\n", encoding="utf-8")
			file_c.write_text("# C\n\n✅ `SomeAPI`\n", encoding="utf-8")
			pairs = [(f, f.read_text()) for f in [file_a, file_b, file_c]]
			findings = health._check_contradictions(pairs, root, "my-skill")
			contradiction_findings = [f for f in findings if f.type == "CONTRADICTING_RULES"]
			self.assertEqual(len(contradiction_findings), 1)

	# ── Integration: audit_skills picks up new checks ───────────────────────

	def test_audit_oss_skill_too_long_emits_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			output = root / "out"
			output.mkdir()
			long_content = "---\nname: my-skill\ndescription: x\napplyTo: '**'\n---\n" + "\n".join(["line"] * 300)
			(root / "SKILL.md").write_text(long_content, encoding="utf-8")
			count = health.audit_skills(root, output, apply_autofix=False, oss=True)
			audit = json.loads((output / "skills-audit.json").read_text(encoding="utf-8"))
			types = [f["type"] for f in audit["findings"]]
			self.assertIn("SKILL_TOO_LONG", types)

	def test_audit_oss_contradiction_emits_finding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			output = root / "out"
			output.mkdir()
			(root / "SKILL.md").write_text(
				"---\nname: my-skill\ndescription: x\napplyTo: '**'\n---\n# A\n\n❌ `SomeAPI`\n",
				encoding="utf-8",
			)
			refs = root / "references"
			refs.mkdir()
			(refs / "details.md").write_text("# B\n\n✅ `SomeAPI`\n", encoding="utf-8")
			count = health.audit_skills(root, output, apply_autofix=False, oss=True)
			audit = json.loads((output / "skills-audit.json").read_text(encoding="utf-8"))
			types = [f["type"] for f in audit["findings"]]
			self.assertIn("CONTRADICTING_RULES", types)


if __name__ == "__main__":
	unittest.main()
