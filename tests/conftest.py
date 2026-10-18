import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch import merge  # noqa: E402


@pytest.fixture
def real_rows():
    """48 real hours of Munich data captured from Open-Meteo on 18 Oct 2026."""
    data = json.loads((Path(__file__).parent / "fixtures" / "sample_api.json").read_text())
    return merge(data["air"], data["weather"], now=datetime(2026, 10, 18, 23, 0))
