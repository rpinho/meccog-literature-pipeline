#!/bin/sh
# Kaji 2024 (pmid39419029, H3), general OK 11-23 for ~8 Codex calls AFTER the Codex weekly reset (Tue 11-24 ~18:40 ET).
# extract 1, referee <=2, scope 1 (this paper only), figure read <=3, 2 in flight at most. Audit (1 call) is a separate step.
PY=~/.local/state/meccog-jobs/venv/bin/python
K=pmid39419029
cd ~/dev/meccog-literature-pipeline/pipeline
L=../runs
# wait for a current weekly Codex snapshot (the wrapper refuses batch calls without one after a reset); give up 11-27
until /usr/bin/python3 -c "import sys,time;sys.path.insert(0,\"$HOME/.local/share/research-harness/rstack/tools\");import _codex_budget as b;sys.exit(b.weekly_snapshot(b.config(),time.time()) is None)" 2>/dev/null; do [ "$(date +%Y%m%d)" -ge 20261127 ] && { echo "NO SNAPSHOT by 11-27"; exit 1; }; sleep 600; done
date
stop() { if [ -f $L/USAGE_LIMIT ] || grep -qi "usage limit\|budget exhausted\|rc=75" $1 2>/dev/null; then echo "STOP after $1"; exit 1; fi; }
MECCOG_MAX_CALLS=1 $PY extract.py H3 --keys $K --workers 1 > $L/b9_extract.log 2>&1; stop $L/b9_extract.log
RC=$($PY -c "
import json,math,os
p='../data/H3/findings/$K.json'
print(min(2, math.ceil(len(json.load(open(p))['findings'])/20)) if os.path.exists(p) else 0)")
echo "findings file -> referee calls $RC"
[ "$RC" -gt 0 ] || { echo "NO FINDINGS"; exit 1; }
MECCOG_MAX_CALLS=$RC $PY referee.py H3 --keys $K --workers 1 > $L/b9_referee.log 2>&1; stop $L/b9_referee.log
MECCOG_MAX_CALLS=1 $PY -c "
import json,pathlib,scope
hyp={h['id']:h for h in json.load(open('../config/hypotheses.json'))['hypotheses']}['H3']
var=json.load(open('../config/variables.json'))['H3']
r=scope.run(pathlib.Path('../data/H3/findings/$K.json'),hyp,var)
fs=[f for f in r['findings'] if 'scope' in f]; print('scope keep',sum(f['scope']['keep'] for f in fs),'drop',sum(not f['scope']['keep'] for f in fs))
" > $L/b9_scope.log 2>&1; stop $L/b9_scope.log
$PY figread.py H3 --dry-run > $L/b9_figread.log 2>&1
MECCOG_MAX_CALLS=3 $PY figread.py H3 >> $L/b9_figread.log 2>&1  # a refused 4th figure is fine; build anyway
$PY build_sheet.py H3 > $L/b9_build.log 2>&1
grep -c . $L/llm_calls.jsonl
date
echo BATCH9 DONE
