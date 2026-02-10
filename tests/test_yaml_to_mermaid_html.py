import yaml
from tools import yaml_to_mermaid


def test_generate_html_contains_pkg_json(tmp_path):
    repo_example = tmp_path / "full_example.yaml"
    from pathlib import Path
    repo_example.write_text((Path(__file__).parent.parent / "examples" / "full_example.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    mermaid, pkg_info = yaml_to_mermaid.generate_mermaid(yaml.safe_load(repo_example.read_text(encoding='utf-8')))
    html = yaml_to_mermaid.generate_html(mermaid, pkg_info)
    assert "<script" in html
    assert "pkg-list" in html
    # package names should be present in the JSON blob
    assert '"Core"' in html
    assert 'showPkg' in html
