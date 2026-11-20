import json,glob,sys,pathlib
D=pathlib.Path(__file__).parent
papers={}; rows={}
for p in glob.glob(str(D/"packet_*.json")):
    for g in json.load(open(p)):
        papers[(g["hyp"],g["paper_id"])]={k:g[k] for k in ("key","hyp","hypothesis","text","supp","figures","pdf")}
        for r in g["rows"]: rows[(g["hyp"],r["Paper/Finding ID"])]=r
names=sys.argv[1:]
items=[]
for n in names:
    for a in json.load(open(D/f"result_{n}.json")):
        if a["verdict"]=="OK": continue
        pid=a["finding_id"].split(".")[0]
        items.append({"src":n,"paper":papers[(a["hyp"],pid)],"row":rows[(a["hyp"],a["finding_id"])],"proposal":a})
items.sort(key=lambda i:(i["paper"]["key"]))
# chunks of ~25 items, never splitting a paper
chunks=[[]]
for it in items:
    if len(chunks[-1])>=25 and chunks[-1][-1]["paper"]["key"]!=it["paper"]["key"]: chunks.append([])
    chunks[-1].append(it)
for i,c in enumerate(chunks):
    for j,it in enumerate(c,1): it["item"]=j
    out=D/f"verify_{'_'.join(names)}_{i}.json"; json.dump(c,open(out,"w"),indent=1,ensure_ascii=False,default=str); print(out.name,len(c))
