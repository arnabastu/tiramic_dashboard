"""Smoke test: every page must run without raising an exception."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["app.py", "pages/1_Live_Monitor.py", "pages/2_System_Efficiency.py", "pages/3_Repair_Proof.py",
         "pages/4_Data_Lab.py", "pages/5_Scale_and_Cost.py"]


@pytest.mark.parametrize("page", PAGES)
def test_page_runs(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]