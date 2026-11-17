"""One place that calls a model. Every call is logged with its exact model id.

Backend: the Codex CLI (`codex exec`), read-only sandbox, one prompt in, last
message out. The model id is pinned (an alias moves; the Method sheet needs the
exact version).
"""
import json
import os
import pathlib
import subprocess
import tempfile
import time

MODEL = os.environ.get("MECCOG_MODEL", "gpt-6.1-sol")
# Lane limit (harness, 11-17): at most 2 Codex processes at once, whatever the thread pools above ask for.
import threading
_SLOTS = threading.BoundedSemaphore(int(os.environ.get("MECCOG_MAX_CODEX", "2")))
# Hard budget per process: MECCOG_MAX_CALLS calls, then every call refuses (the approved plan is a call count).
_BUDGET = [int(os.environ.get("MECCOG_MAX_CALLS", "0"))]  # 0 = refuse all: a run must state its budget
_BUDGET_LOCK = threading.Lock()
LOG = pathlib.Path(__file__).resolve().parent.parent / "runs" / "llm_calls.jsonl"


def ask(prompt, model=MODEL, timeout=1800, effort=None, images=()):
    if (LOG.parent / "USAGE_LIMIT").exists():
        raise RuntimeError("codex usage limit flag present (runs/USAGE_LIMIT); remove it after the reset")
    with _BUDGET_LOCK:
        if _BUDGET[0] <= 0:
            raise RuntimeError("call budget exhausted (set MECCOG_MAX_CALLS to the approved count)")
        _BUDGET[0] -= 1
    with _SLOTS:
        return _ask(prompt, model, timeout, effort, images)


def _ask(prompt, model, timeout, effort, images):
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "last.txt"
        cmd = ["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-m", model,
               "-o", str(out)]
        if effort:
            cmd += ["-c", f"model_reasoning_effort={effort}"]
        for im in images:
            cmd += ["-i", str(im)]
        cmd += ["-"]
        t0 = time.time()
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=td)
        text = out.read_text() if out.exists() else ""
        import re as _re
        tok = _re.search(r"tokens used\s*\n?\s*([\d,]+)", p.stderr + p.stdout)
        tokens = int(tok.group(1).replace(",", "")) if tok else None
        if "usage limit" in (p.stderr + p.stdout).lower():
            LOG.parent.mkdir(exist_ok=True)
            (LOG.parent / "USAGE_LIMIT").write_text(time.strftime("%Y-%m-%dT%H:%M:%S") + "\n" + p.stderr[-400:])
            raise RuntimeError("codex usage limit reached")
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model,
                                "effort": effort, "secs": round(time.time() - t0, 1), "rc": p.returncode,
                                "prompt_chars": len(prompt), "out_chars": len(text), "tokens": tokens}) + "\n")
        if p.returncode != 0 and not text:
            raise RuntimeError(f"codex rc={p.returncode}: {p.stderr[-800:]}")
        return text


def json_lines(text):
    """Parse a JSON array or JSON-lines answer, tolerating a fenced block,
    raw control characters inside strings, and prose around the array."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    t = t.strip()
    dec = json.JSONDecoder(strict=False)
    if "[" in t and not t.startswith("{"):
        start = t.index("[")
        try:
            return dec.raw_decode(t[start:])[0]
        except json.JSONDecodeError:
            pass
    out = []
    for l in t.splitlines():
        l = l.strip().rstrip(",")
        if l.startswith("{"):
            try:
                out.append(dec.raw_decode(l)[0])
            except json.JSONDecodeError:
                pass
    return out


def json_obj(text):
    """One JSON object from an answer (fences, control characters, prose tolerated)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.JSONDecoder(strict=False).raw_decode(t[t.index("{"):])[0]
