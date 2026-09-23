"""Independent structural fidelity gate over source geometry (no question IDs)."""
import re
import hashlib
from statistics import median

SIGNAL = re.compile(r"[=+\u2212\u00b7\u22c5\u03c0\u221a\u00d7\u00f7^\u00b2\u00b3\u2264\u2265]")

def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]

def box(item):
    return [float(item.x), float(item.y), float(item.x + item.width), float(item.y + item.height)]

def validate_and_order(blocks, items, objects, evidence_id, source_id):
    """Check type and expression relations; order by inline baseline, then x.

    An unsupported connected expression becomes one pending candidate. Its
    proposed blocks are evidence only, not additional consumers of its sources.
    """
    im = {source_id(i, "text"): i for i in items}
    om = {source_id(o, "object"): o for o in objects}
    nodes = []
    for block in blocks:
        refs = block.get("source_ids", [])
        parts = ([{**block, "text": im[s].text.strip(), "source_ids": [s]} for s in refs]
                 if block["type"] == "text" and refs and all(s in im for s in refs)
                 else [dict(block)])
        for part in parts:
            refs = part.get("source_ids", [])
            members = [im[s] for s in refs if s in im]
            bounds = [box(i) for i in members] + [om[s]["bbox_ll"] for s in refs if s in om]
            b = union(bounds) if bounds else [0, 0, 0, 0]
            y = median([float(i.y) for i in members]) if members else b[3]
            if part["type"] == "math":
                bars = [om[s]["bbox_ll"] for s in refs if s in om
                        and om[s].get("type") == "PdfObject"
                        and om[s]["bbox_ll"][3] - om[s]["bbox_ll"][1] <= 2.5]
                if bars:
                    axis = median((r[1] + r[3])/2 for r in bars)
                    neighbors = [i for i in items if source_id(i, "text") not in refs
                                 and not i.text.startswith("[Image:")
                                 and b[1] - 1 <= i.y <= b[3]
                                 and (i.x + i.width <= b[0]+1 or i.x >= b[2]-1)
                                 and min(abs(i.x+i.width-b[0]), abs(i.x-b[2])) < 32]
                    y = (float(min(neighbors, key=lambda i: abs(i.y-(axis-3.5))).y)
                         if neighbors else (min(i.y for i in members)+max(i.y for i in members))/2)
                part["display"] = not any(abs(i.y-y) < 1.5 and source_id(i, "text") not in refs
                                          and not i.text.startswith("[Image:") for i in items)
            nodes.append({"block": part, "box": b, "y": y})
    baselines = [n["y"] for n in nodes]
    for n in nodes:
        n["y"] = round(median(y for y in baselines if abs(y-n["y"]) <= .75), 2)
    nodes.sort(key=lambda n: (-n["y"], n["box"][0]))
    parent = list(range(len(nodes)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def numeric(n):
        text = n["block"].get("text", "")
        return n["block"]["type"] == "text" and bool(
            re.fullmatch(r"[\d.,()\[\]+\-\u2212]+", text) and re.search(r"[\d()\[\]+\-\u2212]", text)
            or re.search(r"\d\s*$|^\d+[)]|[(]\s*$", text))
    def mathlike(n):
        return n["block"]["type"] == "math" or bool(SIGNAL.search(n["block"].get("text", "")))
    for i, left in enumerate(nodes):
        for j in range(i+1, len(nodes)):
            right = nodes[j]
            if left["block"]["type"] not in {"math","text"} or right["block"]["type"] not in {"math","text"}:
                continue
            if not ((mathlike(left) and (mathlike(right) or numeric(right))) or (mathlike(right) and numeric(left))):
                continue
            a,b = sorted([left,right], key=lambda n:n["box"][0])
            gap = b["box"][0]-a["box"][2]
            aligned = abs(a["y"]-b["y"]) <= 2
            raised = abs(a["y"]-b["y"]) <= 22 and (numeric(a) or numeric(b))
            if not (-2 <= gap <= 24 and (aligned or raised)):
                continue
            barrier = any(n is not left and n is not right and n["block"]["type"] == "text"
                          and n["box"][0] >= a["box"][2]-.5 and n["box"][2] <= b["box"][0]+.5
                          and abs(n["y"]-a["y"]) < 2 and re.search(r"[a-zA-Z]", n["block"].get("text",""))
                          for n in nodes)
            if not barrier:
                parent[find(j)] = find(i)
    groups = {}
    for i in range(len(nodes)):
        groups.setdefault(find(i), []).append(nodes[i])
    result = []
    for group in groups.values():
        refs = list(dict.fromkeys(s for n in group for s in n["block"].get("source_ids", [])))
        maths = [n for n in group if n["block"]["type"] == "math"]
        reasons = []
        if any(SIGNAL.search(n["block"].get("text", "")) for n in group):
            reasons.append("math_represented_as_text")
        if maths and len(group)>1:
            reasons.append("expression_relations_unproven")
        mixed = (len(group)==2 and len(maths)==1 and group[0]["block"]["type"]=="text"
                 and re.fullmatch(r"\d+", group[0]["block"].get("text",""))
                 and maths[0]["block"].get("latex","").startswith(r"\frac")
                 and abs(group[0]["y"]-maths[0]["y"])<1.5
                 and 0<=maths[0]["box"][0]-group[0]["box"][2]<=8)
        block = dict(group[0]["block"])
        if mixed:
            block = {**maths[0]["block"], "latex":group[0]["block"]["text"]+maths[0]["block"]["latex"], "source_ids":refs}
            reasons = []
        group_box = union([n["box"] for n in group])
        # The layout extractor can omit tall parentheses encoded in a PDF font.
        # Retain their source objects for AI instead of inventing their meaning.
        missing_glyphs = [
            (sid, obj) for sid, obj in om.items()
            if obj.get("type") == "PdfTextObj"
            and obj["bbox_ll"][3] - obj["bbox_ll"][1] > 22
            and group_box[0]-12 <= (obj["bbox_ll"][0]+obj["bbox_ll"][2])/2 <= group_box[2]+12
            and group_box[1] <= (obj["bbox_ll"][1]+obj["bbox_ll"][3])/2 <= group_box[3]
            and not any(
                item.x <= (obj["bbox_ll"][0]+obj["bbox_ll"][2])/2 <= item.x+item.width
                and item.y <= (obj["bbox_ll"][1]+obj["bbox_ll"][3])/2 <= item.y+item.height
                for item in items if not item.text.startswith("[Image:")
            )
        ] if maths else []
        if missing_glyphs:
            reasons.append("untranscribed_grouping_glyph")
            refs = list(dict.fromkeys(refs + [sid for sid, _ in missing_glyphs]))
            group_box = union([group_box] + [obj["bbox_ll"] for _, obj in missing_glyphs])
        if any(r"\begin{cases}" in n["block"].get("latex","") for n in maths):
            reasons.append("system_grouping_requires_evidence")
        if reasons:
            block = {"type":"unresolved", "reason":"structural_fidelity_unproven",
                     "evidence_id":evidence_id, "owner":block.get("owner"), "source_ids":refs,
                     "candidate_type":"math", "candidate_blocks":[n["block"] for n in group],
                     "ai_on_demand":{"status":"pending", "task":"transcribe_expression_and_relations"}}
        if reasons or block["type"] == "math":
            block["candidate_id"] = "math-" + hashlib.sha256("|".join(sorted(refs)).encode()).hexdigest()[:16]
        block["structural_fidelity"] = {
            "status":"unresolved" if reasons or block["type"]=="unresolved" else "verified",
            "reasons":reasons, "bbox_ll":group_box,
            "baseline":min(n["y"] for n in group), "source_ids":refs,
            "representation_type": block["type"],
            "method":"source_geometry_and_atomic_relations_v1"}
        result.append(block)
    result.sort(key=lambda b:(-b["structural_fidelity"]["baseline"], b["structural_fidelity"]["bbox_ll"][0]))
    # Rejoin adjacent prose after expression boundaries have been established.
    # Otherwise a renderer concatenating blocks would lose inter-word spaces.
    joined = []
    for block in result:
        if joined and block["type"] == joined[-1]["type"] == "text":
            prior = joined[-1]
            left, right = prior["structural_fidelity"], block["structural_fidelity"]
            gap = right["bbox_ll"][0] - left["bbox_ll"][2]
            if left["baseline"] == right["baseline"] and 0 <= gap < 24:
                prior["text"] += (" " if gap > 1.2 else "") + block["text"]
                prior["source_ids"].extend(block["source_ids"])
                left["source_ids"] = list(prior["source_ids"])
                left["bbox_ll"] = union([left["bbox_ll"], right["bbox_ll"]])
                continue
        joined.append(block)
    return joined

def fidelity_report(blocks):
    failures = []
    previous = {}
    for b in blocks:
        proof = b.get("structural_fidelity", {})
        if proof.get("status") != "verified":
            failures.append({"source_ids": b.get("source_ids", []),
                             "reasons":proof.get("reasons") or ["unverified_structure"]})
        if b.get("type") == "text" and SIGNAL.search(b.get("text", "")):
            failures.append({"source_ids": b.get("source_ids", []), "reasons":["math_represented_as_text"]})
        if proof:
            if proof.get("source_ids") != b.get("source_ids"):
                failures.append({"source_ids": b.get("source_ids", []), "reasons":["changed_source_membership"]})
            if proof.get("representation_type", b.get("type")) != b.get("type"):
                failures.append({"source_ids": b.get("source_ids", []), "reasons":["changed_representation_type"]})
            owner = b.get("owner")
            if proof.get("baseline") is None or not proof.get("bbox_ll"):
                failures.append({"source_ids": b.get("source_ids", []), "reasons":["missing_source_geometry"]})
            else:
                key = (-proof["baseline"], proof["bbox_ll"][0])
                if owner in previous and key < previous[owner]:
                    failures.append({"source_ids": b.get("source_ids", []), "reasons":["reading_order_violation"]})
                previous[owner] = key
        if b.get("type")=="table":
            for row in b.get("rows",[]):
                for cell in row.get("cells",[]):
                    failures.extend(fidelity_report(cell.get("blocks",[]))["failures"])
    return {"complete":not failures, "failures":failures}
