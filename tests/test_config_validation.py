from pathlib import Path
import subprocess, sys


ROOT=Path(__file__).resolve().parents[1]


def test_example_configs_validate():
    result=subprocess.run([sys.executable, str(ROOT/"scripts/validate_configs.py")], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "failures: 0" in result.stdout
