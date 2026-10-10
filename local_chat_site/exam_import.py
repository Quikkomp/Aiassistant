"""Offline helpers for tolerant model JSON and numbered exam-paper extraction."""

import json
import re


class ExamImportError(ValueError):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage


def question_type(text, default="short_answer"):
    if len(re.findall(r"(?m)^\s*[A-D][.):：、]\s*\S", text)) >= 2:
        return "multiple_choice"
    if re.search(r"_{3,}|\[\s*blank\s*\]", text, re.I):
        return "fill_blank"
    return default if default in {"short_answer", "fill_blank", "multiple_choice"} else "short_answer"


def parse_model_questions(content):
    """Accept arrays, question wrappers, fenced JSON and JSON with surrounding prose."""
    if not isinstance(content, str):
        return []
    decoder = json.JSONDecoder()
    # Decode whole JSON structures, not individual objects inside a malformed array.
    for match in re.finditer(r"[\[{]", content):
        try:
            data, _ = decoder.raw_decode(content[match.start():])
        except ValueError:
            continue
        if isinstance(data, dict):
            data = data.get("questions", data.get("items"))
        if not isinstance(data, list):
            continue
        items = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("question"), str):
                continue
            text = item["question"].strip()
            if text:
                items.append({**item, "question": text})
        if items:
            return items
    return []


def split_numbered_questions(raw_text, default="short_answer"):
    """Preserve exam sections, subquestion numbers, shared stems and multiline text."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    text = re.sub(r"(?im)^[^\n]*\bPage\s+\d+\s+of\s+\d+[^\n]*$", "", text)
    # Explicit Question headings let us exclude numbered cover-page instructions.
    heading = re.compile(r"(?im)^\s*(?:Question\s+|Q)(\d+)\b[^\n]*")
    headings = list(heading.finditer(text))
    sections = [(text[h.start(): headings[i + 1].start() if i + 1 < len(headings) else len(text)], h.group(1))
                for i, h in enumerate(headings)] if headings else [(text, None)]
    results = []
    for section, major_index in sections:
        if major_index:
            header, _, body = section.strip().partition("\n")
        else:
            header, body = "", section
        # 1.1., 2.3), 1., 2)、第1题; avoid decimal constants and mark totals.
        pattern = re.compile(r"(?m)^\s*(?P<index>\d+(?:\.\d+)*|第[一二三四五六七八九十百\d]+题)"
                             r"(?:[.)、：:]|(?<=题))\s+(?=\S)")
        starts = list(pattern.finditer(body))
        if major_index:
            nested = [m for m in starts if m.group("index").startswith(major_index + ".")]
            # Plain numbered lines inside code/answers belong to their enclosing question.
            starts = nested
        if starts:
            preamble = body[:starts[0].start()].strip() if major_index else ""
            for i, start in enumerate(starts):
                block = body[start.start(): starts[i + 1].start() if i + 1 < len(starts) else len(body)].strip()
                if preamble:
                    block = preamble + "\n\n" + block
                meta = {"index": start.group("index"), "extraction_method": "numbered_text"}
                if header:
                    meta["section"] = header
                results.append({"question": block, "question_type": question_type(block, default), "meta": meta})
        elif major_index and body.strip():
            results.append({"question": section.strip(), "question_type": question_type(body, default),
                            "meta": {"index": "Q" + major_index, "section": header, "extraction_method": "numbered_text"}})
    return results
