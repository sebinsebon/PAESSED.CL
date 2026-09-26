"""Conservative, auxiliary geometry for atomic numeric fractions.

No original coordinates are replaced. Matching is an exact-text, font and
origin constraint (0.002 pt accounts only for serialization/float rounding),
never a nearest-glyph search. Unsupported transforms deliberately abstain.
"""
import math
import re
from collections import Counter

EPS = .002


def numeric_glyph_matches(items, objects):
    pairs = []
    for item in items:
        text = item.text.strip()
        if not re.fullmatch(r"[0-9]+", text):
            continue
        for obj in objects:
            if obj.get("type") != "PdfTextObj" or obj.get("pdfium_text") != text:
                continue
            matrix = obj.get("pdfium_matrix", [])
            if (len(matrix) != 6 or obj.get("pdfium_page_rotation") != 0
                    or obj.get("pdfium_nesting_level") != 0
                    or obj.get("pdfium_page_number") != getattr(item, "page", None)):
                continue
            a, b, c, d, x, y = matrix
            size = obj.get("font_size", 0)
            declared = obj.get("font_size_declared", 0)
            if not all(math.isfinite(v) for v in [*matrix, size, declared]):
                continue
            if a <= 0 or d <= 0 or abs(b) > 1e-8 or abs(c) > 1e-8 or size <= 0:
                continue
            if declared <= 0 or abs(declared*d-size) > EPS:
                continue
            # The extractor's em-box convention is accepted only when all
            # independent constraints agree for this particular token/object.
            if (abs(float(item.x)-x) <= EPS
                    and abs(float(item.y)+float(item.font_size)-y) <= EPS
                    and abs(float(item.font_size)-size) <= EPS):
                pairs.append((item, obj))
    ic = Counter(id(i) for i, _ in pairs)
    oc = Counter(id(o) for _, o in pairs)
    return [(i, o) for i, o in pairs if ic[id(i)] == oc[id(o)] == 1]


def simple_fraction_groups(items, objects):
    """Return disjoint proven groups; ambiguity leaves all sources untouched."""
    matches = numeric_glyph_matches(items, objects)
    matched_boxes = {id(i): o["bbox_ll"] for i, o in matches}
    groups = []
    for bar in objects:
        if (bar.get("type") != "PdfObject" or bar.get("pdfium_nesting_level") != 0
                or bar.get("pdfium_page_rotation") != 0):
            continue
        x0, y0, x1, y1 = bar["bbox_ll"]
        width, thickness = x1-x0, y1-y0
        if width <= 0 or thickness <= 0:
            continue
        above, below = [], []
        for token, glyph in matches:
            l, b, r, t = glyph["bbox_ll"]
            size = glyph["font_size"]
            if not (0 < thickness <= .1*size and width <= 2*size
                    and x0-EPS <= l < r <= x1+EPS
                    and abs((l+r-x0-x1)/2) <= .15*size):
                continue
            if 0 < b-y1 <= .75*size:
                above.append((token, glyph))
            if 0 < y0-t <= .75*size:
                below.append((token, glyph))
        if len(above) != 1 or len(below) != 1:
            continue
        (num, ng), (den, dg) = above[0], below[0]
        if not (bar.get("pdfium_page_number") == ng["pdfium_page_number"] == dg["pdfium_page_number"]):
            continue
        if num is den or abs(ng["font_size"]-dg["font_size"]) > EPS:
            continue
        size = ng["font_size"]
        if width > 1.6*max(float(num.width), float(den.width)):
            continue
        top, bottom = ng["bbox_ll"][3], dg["bbox_ll"][1]
        upper_gap = ng["bbox_ll"][1]-y1
        lower_gap = y0-dg["bbox_ll"][3]
        if abs(upper_gap-lower_gap) > .3*size:
            continue
        own = {id(bar), id(ng), id(dg)}
        # Any other visible object entering the vertical column invalidates
        # isolation: connected table edges, duplicate bars or missing glyphs.
        def intersects_column(o):
            l,b,r,t = o["bbox_ll"]
            return (l < r or b < t) and l <= x1+EPS and r >= x0-EPS and b < top and t > bottom
        if any(id(o) not in own and intersects_column(o) for o in objects):
            continue
        # A token without a matching glyph must not disappear from a cluster.
        # This is a rejection window only; it never relocates that token.
        def token_enters_column(i):
            l, b, r, t = matched_boxes.get(id(i),
                [float(i.x), float(i.y), float(i.x+i.width), float(i.y+i.height)])
            return l < x1+.25*size and r > x0-.25*size and b < top and t > bottom
        if any(i is not num and i is not den and i.text.strip() and token_enters_column(i)
               for i in items):
            continue
        # Reject an inline minus/underline in a surrounding expression. Use
        # visible geometry where available; never shift unrelated text boxes.
        axis = (y0+y1)/2
        def option_label_glyph(o):
            matrix = o.get("pdfium_matrix", [])
            return len(matrix) == 6 and any(
                re.fullmatch(r"[A-E]\)", i.text.strip())
                and o.get("pdfium_text", "").strip() in {i.text.strip(), i.text.strip()[0], ")"}
                and float(i.x)-EPS <= matrix[4] <= float(i.x+i.width)+EPS
                and abs(matrix[5]-float(i.y+i.font_size)) <= EPS
                and abs(o.get("font_size", 0)-float(i.font_size)) <= EPS
                for i in items)
        if any(id(o) not in own and o.get("type") == "PdfTextObj"
               and o["bbox_ll"][1] <= axis <= o["bbox_ll"][3]
               and o["bbox_ll"][2] >= x0-2*size
               and o["bbox_ll"][0] <= x1+2*size
               and o.get("pdfium_text", "").strip()
               and not option_label_glyph(o)
               for o in objects):
            continue
        groups.append({"items": [num, den], "glyphs": [ng, dg], "bar": bar})
    uses = Counter(id(v) for g in groups for v in [*g["items"], *g["glyphs"], g["bar"]])
    return [g for g in groups if all(uses[id(v)] == 1 for v in [*g["items"], *g["glyphs"], g["bar"]])]
