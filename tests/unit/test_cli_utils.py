from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.tools.cli_utils import emit_json, emit_json_result


def test_emit_json_prints_one_parseable_document(capsys):
    emit_json({"ok": True, "label": "测试", "path": Path("outputs/report.json")})

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "label": "测试",
        "path": str(Path("outputs/report.json")),
    }


def test_emit_json_result_uses_ok_for_exit_code(capsys):
    assert emit_json_result({"ok": True}, failure_code=7) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert emit_json_result({"ok": False}, failure_code=7) == 7
    assert json.loads(capsys.readouterr().out)["ok"] is False
