from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skills_evolution import ai_updater


def make_skill(tmp_dir: str, content: str, agent_dir: str = ".github") -> tuple[Path, Path, str]:
	repo_root = Path(tmp_dir) / "repo"
	skill_dir = repo_root / agent_dir / "skills" / "tca-standards"
	skill_dir.mkdir(parents=True)
	skill_path = skill_dir / "SKILL.md"
	skill_path.write_text(content, encoding="utf-8")
	return repo_root, skill_path, str(skill_path.relative_to(repo_root))


class ApplyPatchesTests(unittest.TestCase):
	def test_unique_match_is_applied(self) -> None:
		content = "# TCA\n\nUse TCA 1.5 pattern.\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content)
			patches = [{"old_text": "TCA 1.5", "new_text": "TCA 1.10", "reason": "bump"}]
			applied, skipped, ambiguous = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual((applied, skipped, ambiguous), (1, 0, 0))
			self.assertIn("TCA 1.10", path.read_text())
			self.assertNotIn("TCA 1.5", path.read_text())

	def test_not_found_is_skipped(self) -> None:
		content = "# TCA\n\nNo version here.\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content)
			patches = [{"old_text": "TCA 1.5", "new_text": "TCA 1.10", "reason": "bump"}]
			applied, skipped, _ = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual(applied, 0)
			self.assertEqual(skipped, 1)
			self.assertEqual(path.read_text(), content)

	def test_duplicate_match_is_ambiguous(self) -> None:
		content = "TCA 1.5 pattern.\nSee also TCA 1.5.\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content)
			patches = [{"old_text": "TCA 1.5", "new_text": "TCA 1.10", "reason": "bump"}]
			applied, _, ambiguous = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual(applied, 0)
			self.assertEqual(ambiguous, 1)
			self.assertEqual(path.read_text(), content)

	def test_path_outside_skills_is_rejected(self) -> None:
		content = "# Bad\n"
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = Path(tmp) / "repo"
			repo_root.mkdir()
			bad_path = repo_root / "some" / "other" / "file.md"
			bad_path.parent.mkdir(parents=True)
			bad_path.write_text(content)
			patches = [{"old_text": "Bad", "new_text": "Replaced", "reason": "test"}]
			applied, _, _ = ai_updater.apply_patches(patches, bad_path, "some/other/file.md", content)
			self.assertEqual(applied, 0)
			self.assertEqual(bad_path.read_text(), content)

	def test_claude_skills_path_is_allowed(self) -> None:
		content = "# TCA\n\nUse TCA 1.5 pattern.\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content, agent_dir=".claude")
			self.assertTrue(rel.startswith(".claude/skills/"))
			patches = [{"old_text": "TCA 1.5", "new_text": "TCA 1.10", "reason": "bump"}]
			applied, _, _ = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual(applied, 1)

	def test_multiple_patches_applied_sequentially(self) -> None:
		content = "Use TCA 1.5 and Factory 2.1.\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content)
			patches = [
				{"old_text": "TCA 1.5", "new_text": "TCA 1.10", "reason": "TCA bump"},
				{"old_text": "Factory 2.1", "new_text": "Factory 2.4", "reason": "Factory bump"},
			]
			applied, _, _ = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual(applied, 2)
			updated = path.read_text()
			self.assertIn("TCA 1.10", updated)
			self.assertIn("Factory 2.4", updated)

	def test_empty_old_text_is_skipped(self) -> None:
		content = "# TCA\n"
		with tempfile.TemporaryDirectory() as tmp:
			_, path, rel = make_skill(tmp, content)
			patches = [{"old_text": "", "new_text": "anything", "reason": "empty"}]
			applied, skipped, _ = ai_updater.apply_patches(patches, path, rel, content)
			self.assertEqual((applied, skipped), (0, 1))


class DiscoverDepsTests(unittest.TestCase):
	def test_parses_package_resolved_v3(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = Path(tmp)
			resolved = {
				"pins": [
					{
						"identity": "swift-composable-architecture",
						"location": "https://github.com/pointfreeco/swift-composable-architecture",
						"state": {"version": "1.10.0"},
					},
					{
						"identity": "private-dep",
						"location": "https://example.com/private/dep",
						"state": {"revision": "def"},
					},
				],
				"version": 3,
			}
			(repo_root / "Package.resolved").write_text(json.dumps(resolved))
			deps = ai_updater.discover_deps(repo_root)
			self.assertEqual(len(deps), 1)
			self.assertEqual(deps[0]["alias"], "swift-composable-architecture")
			self.assertEqual(deps[0]["repo"], "pointfreeco/swift-composable-architecture")
			self.assertEqual(deps[0]["pinned"], "1.10.0")

	def test_parses_package_resolved_v2(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = Path(tmp)
			resolved = {
				"object": {
					"pins": [
						{
							"package": "TCA",
							"repositoryURL": "https://github.com/pointfreeco/swift-composable-architecture.git",
							"state": {"version": "1.5.0"},
						}
					]
				},
				"version": 2,
			}
			(repo_root / "Package.resolved").write_text(json.dumps(resolved))
			deps = ai_updater.discover_deps(repo_root)
			self.assertEqual(len(deps), 1)
			self.assertEqual(deps[0]["repo"], "pointfreeco/swift-composable-architecture")
			self.assertEqual(deps[0]["pinned"], "1.5.0")

	def test_skips_build_directory(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = Path(tmp)
			build_dir = repo_root / ".build" / "checkouts" / "some-pkg"
			build_dir.mkdir(parents=True)
			(build_dir / "Package.resolved").write_text(json.dumps({"pins": [], "version": 3}))
			deps = ai_updater.discover_deps(repo_root)
			self.assertEqual(deps, [])

	def test_handles_non_github_url(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo_root = Path(tmp)
			resolved = {
				"pins": [{"identity": "other", "location": "https://example.com/repo.git", "state": {"version": "1.0.0"}}],
				"version": 3,
			}
			(repo_root / "Package.resolved").write_text(json.dumps(resolved))
			deps = ai_updater.discover_deps(repo_root)
			self.assertEqual(deps, [])


class WriteReportTests(unittest.TestCase):
	def test_no_patches_says_up_to_date(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			output_dir = Path(tmp)
			report = {
				"skills_changed": 0,
				"total_patches_applied": 0,
				"total_patches_skipped": 0,
				"total_patches_ambiguous": 0,
				"by_skill": [],
			}
			ai_updater.write_report(output_dir, report, [])
			md = (output_dir / "skills-ai-updates.md").read_text()
			self.assertIn("up to date", md)

	def test_with_patches_lists_applied(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			output_dir = Path(tmp)
			report = {
				"skills_changed": 1,
				"total_patches_applied": 1,
				"total_patches_skipped": 0,
				"total_patches_ambiguous": 0,
				"by_skill": [
					{
						"skill": "tca-standards",
						"summary": "Updated TCA ref.",
						"applied": 1,
						"patches": [{"old_text": "x", "new_text": "y", "reason": "version bump", "_status": "applied"}],
					}
				],
			}
			deps = [{"alias": "TCA", "repo": "pointfreeco/swift-composable-architecture", "pinned": "1.5.0"}]
			ai_updater.write_report(output_dir, report, deps)
			md = (output_dir / "skills-ai-updates.md").read_text()
			self.assertIn("tca-standards", md)
			self.assertIn("version bump", md)
			self.assertIn("TCA", md)


if __name__ == "__main__":
	unittest.main()
