"""scripts/update_usdclp.py: nunca muestra las token del BCCh y no rompe el CSV."""

import importlib.util
import logging
from pathlib import Path

import httpx
import pytest

from derivados101 import market

ROOT = Path(__file__).resolve().parents[1]
_PASS = "clave-super-secreta-456"


@pytest.fixture
def script(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("update_usdclp", ROOT / "scripts" / "update_usdclp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    csv = tmp_path / "usd.csv"
    csv.write_text("date,usdclp\n2024-01-02,877.12\n")
    monkeypatch.setattr(mod, "DEFAULT_CSV", csv)
    monkeypatch.setattr(mod, "load_usdclp", lambda: market.load_usdclp(csv))
    monkeypatch.setattr(market, "_sleep", lambda s: None)
    monkeypatch.delenv("BCCH_TOKEN", raising=False)
    monkeypatch.setenv("BCCH_USER", "usuario@ejemplo.cl")
    monkeypatch.setenv("BCCH_PASS", _PASS)
    return mod, csv


def _all_fail(monkeypatch, mod):
    def client(timeout):
        return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)), timeout=timeout)

    monkeypatch.setattr(market, "_make_client", client)
    monkeypatch.setattr(mod, "_make_client", client)


def test_script_failure_keeps_csv_and_hides_secret(script, monkeypatch, caplog, capsys):
    mod, csv = script
    _all_fail(monkeypatch, mod)
    before = csv.read_text()
    with caplog.at_level(logging.DEBUG):
        assert mod.main() == 0
    out = capsys.readouterr()
    assert csv.read_text() == before
    for text in (caplog.text, out.out, out.err):
        assert _PASS not in text and "usuario@ejemplo.cl" not in text and "si3.bcentral.cl" not in text


def test_script_uses_bcch_with_user_and_password(script, monkeypatch):
    mod, csv = script
    payload = {"Codigo": 0, "Series": {"Obs": [
        {"indexDateString": "03-01-2024", "value": "884.59", "statusCode": "OK"}]}}

    def client(timeout):
        return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
                            timeout=timeout)

    monkeypatch.setattr(market, "_make_client", client)
    assert mod.main() == 0
    assert csv.read_text().splitlines()[-1] == "2024-01-03,884.59"
