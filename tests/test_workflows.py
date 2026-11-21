"""I workflow della CI: ogni azione e' fissata per SHA di commit (con il tag in un commento), il permesso di scrittura
sui contenuti sta solo nei job che pubblicano, e Dependabot propone gli aggiornamenti."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = sorted(glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")))


def test_every_action_is_pinned_to_a_commit_sha_with_its_tag_in_a_comment():
    assert WORKFLOWS
    for path in WORKFLOWS:
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            m = re.match(r"\s*(?:-\s+)?uses:\s*(\S+)(.*)", line)
            if not m or m.group(1).startswith("./"):
                continue
            action, rest = m.groups()
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", action), f"{os.path.basename(path)}:{n}: {action}"
            assert re.search(r"#\s*v?\d", rest), f"{os.path.basename(path)}:{n}: manca il tag nel commento"


def test_top_level_permissions_do_not_write_contents_and_publishing_jobs_ask_for_it():
    for path in WORKFLOWS:
        text = open(path, encoding="utf-8").read()
        top = re.search(r"^permissions:\n((?:[ ]+.*\n)+)", text, re.M)
        assert top, os.path.basename(path)
        assert "contents: write" not in top.group(1), f"{os.path.basename(path)}: scrittura a livello di workflow"
        if "action-gh-release" in text or "gh release" in text:
            assert re.search(r"^    permissions:\n      contents: write", text, re.M), os.path.basename(path)


def test_dependabot_watches_the_github_actions():
    text = open(os.path.join(ROOT, ".github", "dependabot.yml"), encoding="utf-8").read()
    assert 'package-ecosystem: "github-actions"' in text and 'directory: "/"' in text
