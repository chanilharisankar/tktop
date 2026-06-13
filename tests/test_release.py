import pytest

from tktop.release import get_current_version, update_version_file, validate_version


def test_validate_version_accepts_semver():
    assert validate_version("1.2.3") == "1.2.3"
    assert validate_version(" 0.1.0 ") == "0.1.0"


@pytest.mark.parametrize("version", ["", "1", "1.2", "1.2.3.4", "v1.2.3", "1.2.3-beta"])
def test_validate_version_rejects_invalid(version):
    with pytest.raises(ValueError):
        validate_version(version)


def test_update_version_file(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '\n'.join(
            [
                "[project]",
                'name = "tktop"',
                'version = "0.1.0"',
            ]
        )
        + "\n"
    )

    monkeypatch.setattr("tktop.release.PYPROJECT", pyproject)
    assert get_current_version() == "0.1.0"

    update_version_file("0.2.0")

    content = pyproject.read_text()
    assert 'version = "0.2.0"' in content
    assert 'version = "0.1.0"' not in content
