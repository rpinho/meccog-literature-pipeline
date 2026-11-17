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
LOG = pathlib.Path(__file__).resolve().parent.parent / "runs" / "llm_calls.jsonl"


def ask(prompt, model=MODEL, timeout=1800, effort=None, images=()):
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
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model,
                                "effort": effort, "secs": round(time.time() - t0, 1), "rc": p.returncode,
                                "prompt_chars": len(prompt), "out_chars": len(text)}) + "\n")
        if p.returncode != 0 and not text:
            raise RuntimeError(f"codex rc={p.returncode}: {p.stderr[-800:]}")
        return text


def json_lines(text):
    """Parse a JSON array or JSON-lines answer, tolerating a fenced block."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    t = t.strip()
    if t.startswith("["):
        return json.loads(t)
    return [json.loads(l) for l in t.splitlines() if l.strip().startswith("{")]
