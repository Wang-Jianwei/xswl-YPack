from ypack.config import PackageConfig
from ypack_web.api.project import config_to_dict


def test_config_to_dict_marks_recursive():
    cfg = PackageConfig.from_dict({
        "app": {"name": "T", "version": "1.0"},
        "install": {},
        "files": [{"source": "lib/**/*", "destination": "$INSTDIR"}],
    })

    out = config_to_dict(cfg)
    assert "files" in out
    assert out["files"][0]["source"] == "lib/**/*"
    assert out["files"][0].get("recursive") is True


def test_config_to_dict_omits_recursive_when_not_pattern():
    cfg = PackageConfig.from_dict({
        "app": {"name": "T", "version": "1.0"},
        "install": {},
        "files": [{"source": "bin/*", "destination": "$INSTDIR"}],
    })

    out = config_to_dict(cfg)
    assert "files" in out
    assert out["files"][0]["source"] == "bin/*"
    assert "recursive" not in out["files"][0]
