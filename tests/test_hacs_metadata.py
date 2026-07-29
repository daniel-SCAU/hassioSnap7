"""Compatibility checks for HACS and integration metadata."""
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HACS_PATH = REPO_ROOT / "hacs.json"
MANIFEST_PATH = REPO_ROOT / "custom_components" / "snap7_plc" / "manifest.json"
README_PATH = REPO_ROOT / "README.md"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_hacs_domains_match_manifest_domain():
    hacs = _read_json(HACS_PATH)
    manifest = _read_json(MANIFEST_PATH)
    assert manifest["domain"] in hacs["domains"]


def test_manifest_has_hacs_friendly_metadata():
    manifest = _read_json(MANIFEST_PATH)
    assert manifest["config_flow"] is True
    assert manifest["codeowners"]
    assert manifest["version"]
    assert manifest["documentation"].startswith("https://github.com/daniel-SCAU/hassioSnap7")


def test_readme_contains_hacs_installation_repo_url():
    readme = README_PATH.read_text(encoding="utf-8")
    assert "### HACS (recommended)" in readme
    assert "https://github.com/daniel-SCAU/hassioSnap7" in readme
