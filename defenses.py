"""Defenses for the vendor desk agent.

Layer 1, content checks (code, before the model): drop text a person can't see, then redact
lines that read like instructions to the reviewer.
Layer 2, agent design (code, around the model): the model only extracts facts. Code checks the
facts against the text it was shown, then makes the decision itself from the handbook rules.
Dangerous tools are held for a human (see tools.py).
Layer 3, prompt rules: prompts/prompt.md (selected in agent.py).
"""
import email
import re
import unicodedata
from email import policy
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from pypdf import PdfReader

from models import VendorDeskResult

ZERO_WIDTH = re.compile("[​‌‍⁠﻿­]")
MIN_VISIBLE_PT = 4  # text smaller than this on a printed page is treated as hidden
WHITE = 0.9  # fill color components at or above this count as white

# ---------------------------------------------------------------- Layer 1: hidden text


def _is_white(op: bytes, args: list) -> bool | None:
    """True/False for a colour operator we understand, None otherwise."""
    try:
        vals = [float(a) for a in args]
    except (TypeError, ValueError):
        return None
    if op == b"g" and len(vals) == 1:
        return vals[0] >= WHITE
    if op == b"rg" and len(vals) == 3:
        return all(v >= WHITE for v in vals)
    if op == b"k" and len(vals) == 4:
        return all(v <= 1 - WHITE for v in vals)
    return None


def read_pdf_visible(path: Path) -> tuple[str, list[dict]]:
    """Text a person sees in a PDF viewer, plus what was dropped and why."""
    visible: list[str] = []
    removed: list[dict] = []
    for page in PdfReader(path).pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        state = {"white": False, "invisible_mode": False, "stack": []}

        def before(op, args, cm, tm, state=state):
            if op == b"q":
                state["stack"].append(state["white"])
            elif op == b"Q" and state["stack"]:
                state["white"] = state["stack"].pop()
            elif op in (b"g", b"rg", b"k"):
                white = _is_white(op, args)
                if white is not None:
                    state["white"] = white
            elif op == b"Tr":
                state["invisible_mode"] = bool(args) and int(args[0]) == 3

        def show(text, cm, tm, font_dict, font_size, state=state, width=width, height=height):
            if not text.strip():
                return
            a, b, c, d, e, f = cm
            x = tm[4] * a + tm[5] * c + e
            y = tm[4] * b + tm[5] * d + f
            scale = abs(tm[0] * tm[3] - tm[1] * tm[2]) ** 0.5 * abs(a * d - b * c) ** 0.5
            size = (font_size or 0) * scale
            reason = None
            if state["invisible_mode"]:
                reason = "invisible render mode"
            elif state["white"]:
                reason = "white text"
            elif size < MIN_VISIBLE_PT:
                reason = f"tiny text ({size:.1f} pt)"
            elif not (0 <= x <= width and 0 <= y <= height):
                reason = "positioned off the page"
            if reason:
                removed.append({"reason": reason, "text": text.strip()})
            else:
                visible.append(text.rstrip("\n"))

        page.extract_text(visitor_operand_before=before, visitor_text=show)
    return ZERO_WIDTH.sub("", "\n".join(visible)).strip(), removed


HIDDEN_CSS = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(\.0+)?\s*(;|$)"
    r"|font-size\s*:\s*[0-3](\.\d+)?\s*(px|pt)?\s*(;|$)"
    r"|color\s*:\s*(#fff(fff)?|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))\b"
    r"|(left|top|text-indent)\s*:\s*-\d{3,}"
    r"|(height|width)\s*:\s*0(px)?\s*;[^\"]*overflow\s*:\s*hidden"
    r"|clip(-path)?\s*:\s*(rect\(0|inset\(50%|circle\(0)",
    re.I,
)


def html_visible(html: str) -> tuple[str, list[dict]]:
    """Visible text of an HTML document, plus what was dropped and why."""
    soup = BeautifulSoup(html, "html.parser")
    removed: list[dict] = []
    for node in soup.find_all(string=lambda s: isinstance(s, Comment)):
        removed.append({"reason": "HTML comment", "text": str(node).strip()})
        node.extract()
    for tag in soup(["script", "style", "head", "template", "noscript"]):
        if tag.name in ("script", "template", "noscript") and tag.get_text(strip=True):
            removed.append({"reason": f"<{tag.name}> content", "text": tag.get_text(strip=True)[:300]})
        tag.decompose()
    hidden = soup.find_all(
        lambda t: t.has_attr("hidden")
        or t.get("aria-hidden") == "true"
        or (t.get("style") and HIDDEN_CSS.search(t["style"]))
    )
    for tag in hidden:
        if tag.decomposed:
            continue
        text = tag.get_text(" ", strip=True)
        if text:
            removed.append({"reason": "hidden element", "text": text})
        tag.decompose()
    for tag in soup.find_all(["br", "tr", "p", "li", "h1", "h2", "h3"]):
        tag.append("\n")
    for tag in soup.find_all(["th", "td"]):
        tag.append(" ")
    text = ZERO_WIDTH.sub("", soup.get_text())
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line), removed


def eml_visible(path: Path) -> tuple[str, list[dict]]:
    """Email headers plus the body a person reads. Hidden HTML text is dropped either way."""
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    header = "\n".join(f"{h}: {msg[h]}" for h in ("From", "To", "Subject", "Date") if msg[h])
    removed: list[dict] = []
    plain = msg.get_body(preferencelist=("plain",))
    if plain is not None:
        body = ZERO_WIDTH.sub("", plain.get_content())
    else:
        html_part = msg.get_body(preferencelist=("html",))
        body, removed = html_visible(html_part.get_content()) if html_part else ("", [])
    return f"{header}\n\n{body.strip()}", removed


# ------------------------------------------- Layer 1: instruction-like lines in visible text

INSTRUCTION_LIKE = re.compile(
    r"\b(send_email|approve_payment)\b"
    r"|ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules)"
    r"|\b(system|developer) (prompt|message)\b"
    r"|max(imum)? unit cost list|\bhandbook\b"
    r"|\b(reviewer|agent|assistant|AI)\b[^.\n]{0,60}\b(must|should|needs? to|sends?|approves?|marks?)\b"
    r"|\bmark (the|this) quote as (recommended|approved)\b"
    r"|\bapprove (the )?(\$[\d,]+|deposit|payment)",
    re.I,
)


def redact_instruction_lines(text: str) -> tuple[str, list[dict]]:
    """Replace lines that talk to the reviewer or name our tools; keep everything else."""
    out, removed = [], []
    for line in text.splitlines():
        if INSTRUCTION_LIKE.search(line):
            removed.append({"reason": "instruction-like line", "text": line.strip()})
            out.append("[line removed by document scan: it reads like an instruction, not a quote detail]")
        else:
            out.append(line)
    return "\n".join(out), removed


def read_document_safely(path: Path) -> tuple[str, list[dict]]:
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        text, removed = html_visible(path.read_text(encoding="utf-8", errors="replace"))
    elif suffix == ".pdf":
        text, removed = read_pdf_visible(path)
    elif suffix == ".eml":
        text, removed = eml_visible(path)
    else:
        return f"Error: unsupported file type {suffix!r}; expected .html, .pdf, or .eml.", []
    text = unicodedata.normalize("NFKC", text)
    text, flagged = redact_instruction_lines(text)
    return text, removed + flagged


# ---------------------------------------------------------- Layer 2: rules done in code


def _table_rows(handbook: str, heading: str) -> list[list[str]]:
    """Cells of each data row in the first markdown table after a section heading."""
    section = handbook.split(heading, 1)[1]
    rows = []
    for line in section.splitlines():
        if line.startswith("## ") and rows:
            break
        if line.startswith("|") and not set(line) <= set("|- "):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:]  # drop the header row


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


class Rules:
    """Handbook section 4 purchasing checks, read from the handbook text itself."""

    def __init__(self, handbook: str):
        self.approved = {_norm(r[1]) for r in _table_rows(handbook, "## 5. Approved vendors")}
        self.blocked = {_norm(r[0]): r[1] for r in _table_rows(handbook, "## 6. Removed and pending vendors")}
        self.max_cost = {
            r[0]: float(r[4].replace("$", "").replace(",", ""))
            for r in _table_rows(handbook, "## 9. Product catalogue")
        }
        self.max_lead_days, self.max_min_order = 21, 600

    def decide(self, r: VendorDeskResult, lead_unit: str = "days") -> tuple[str, str]:
        lead = f"{r.lead_time_days} {lead_unit}"
        name = _norm(r.vendor)
        if name in self.blocked:
            return "do_not_recommend", f"The approved-vendor check fails because {r.vendor} is on the removed or pending vendor list."
        if name not in self.approved:
            return "do_not_recommend", f"The approved-vendor check fails because {r.vendor} is not on the approved vendor list."
        cap = self.max_cost.get(r.sku or "")
        if r.unit_price is None or cap is None:
            why = "no unit price is stated" if r.unit_price is None else f"SKU {r.sku} is not in the catalogue"
            return "do_not_recommend", f"The price check fails because {why}."
        if r.unit_price > cap:
            return "do_not_recommend", f"The price check fails because the ${r.unit_price:.2f} unit price exceeds the ${cap:.2f} maximum for {r.sku}."
        if r.lead_time_days is None:
            return "do_not_recommend", "The lead-time check fails because no lead time is stated."
        if r.lead_time_days > self.max_lead_days:
            return "do_not_recommend", f"The lead-time check fails because the quoted lead time of {lead} exceeds the {self.max_lead_days}-day limit."
        if r.min_order is None:
            return "do_not_recommend", "The minimum-order check fails because no minimum order is stated."
        if r.min_order > self.max_min_order:
            return "do_not_recommend", f"The minimum-order check fails because the minimum of {r.min_order} units exceeds the {self.max_min_order}-unit limit."
        return "recommend", f"The approved-vendor, price, lead-time ({lead}), and minimum-order checks all pass."


def _number_in(text: str, value: float | int) -> bool:
    flat = text.replace(",", "")
    candidates = {f"{value:.2f}", f"{value:g}", str(value)}
    return any(re.search(rf"(?<![\d.]){re.escape(c)}(?![\d])", flat) for c in candidates)


def lead_time_unit(text: str, days: int | None) -> str:
    """"business days" if the document states the lead time that way, else "days"."""
    if days is not None and re.search(rf"(?<![\d.]){days}\s*(-\s*)?business[\s-]+days?\b", text, re.I):
        return "business days"
    return "days"


def enforce(result: VendorDeskResult, seen_text: str, rules: Rules) -> tuple[VendorDeskResult, list[dict]]:
    """Check each extracted fact against the text the model saw, then decide in code."""
    events: list[dict] = []
    data = result.model_dump()
    if result.sku and result.sku.lower() not in seen_text.lower():
        events.append({"layer": 2, "event": "sku not found in document text; cleared", "was": result.sku})
        data["sku"] = None
    for field in ("unit_price", "lead_time_days", "min_order"):
        if data[field] is not None and not _number_in(seen_text, data[field]):
            events.append({"layer": 2, "event": f"{field} not found in document text; cleared", "was": data[field]})
            data[field] = None
    if _norm(result.vendor) not in _norm(seen_text):
        events.append({"layer": 2, "event": "vendor name not found in document text", "was": result.vendor})
    checked = VendorDeskResult(**data)
    decision, reason = rules.decide(checked, lead_time_unit(seen_text, checked.lead_time_days))
    if decision != result.decision:
        events.append({"layer": 2, "event": "decision overridden by handbook rules",
                       "model_said": result.decision, "code_says": decision})
    return checked.model_copy(update={"decision": decision, "reason": reason}), events
