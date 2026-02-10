import io
import yaml
from tools import yaml_to_mermaid


def test_generate_mermaid_from_full_example(tmp_path):
    src = (tmp_path / "full_example.yaml")
    # load example from repo examples/full_example.yaml
    import pathlib
    repo_example = pathlib.Path(__file__).parent.parent / "examples" / "full_example.yaml"
    data = repo_example.read_text(encoding="utf-8")
    src.write_text(data, encoding="utf-8")

    with open(src, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    mermaid, pkg_info = yaml_to_mermaid.generate_mermaid(cfg)
    assert isinstance(mermaid, str) and mermaid.startswith("flowchart LR")
    assert "App:" in mermaid
    # Expect at least one package node
    assert "pkg_" in mermaid or "packages: <none>" not in mermaid
    # Detailed fields should appear
    assert "sources:" in mermaid
    assert "post_install" in mermaid
    assert "HKLM" in mermaid or "registry" in mermaid
    assert "MYAPP_HOME" in mermaid
    assert ".my" in mermaid or "file_associations" in mermaid
    assert "(decompress)" in mermaid or "sha256" in mermaid
    # Output must use HTML <br> for line breaks
    assert "<br>" in mermaid
    # pkg_info should contain package metadata
    assert isinstance(pkg_info, dict)
    assert "Core" in pkg_info and pkg_info["Core"]["name"] == "Core"
