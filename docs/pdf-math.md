# Mathematical PDF export

The website uses KaTeX in the browser. The download endpoint uses ReportLab,
which cannot typeset LaTeX on its own; escaping a question into a Paragraph used
to print commands such as `\frac` literally. Chinese font embedding alone does
not fix this separate rendering issue.

`pdf_math.py` now tokenizes the original question, renders each formula using
Matplotlib's offline Mathtext engine at 300 dpi, and inserts it as a transparent
inline image with the correct baseline. Chinese prose stays searchable text in
the bundled Noto Sans SC font. Formulas are images, not searchable math text.
This changes export presentation only, never the stored questions or grading.

## Supported notation

- Inline `\(...\)` and `$...$`; display `\[...\]` and `$$...$$`.
- Powers, subscripts, fractions, roots, integrals, limits, sums, Greek letters,
  ordinary trigonometric/logarithmic functions, and `\text{中文}`.
- `equation`, `align`, `aligned` and `gather` blocks (including starred forms).
  Alignment blocks become separate equation lines; alignment columns are not
  preserved. `\dfrac`/`\tfrac` normalize to `\frac`.
- Backtick code and ordinary currency such as `$10 and $20` stay literal.

Mathtext supports a subset of LaTeX, not the full KaTeX language. Complex
matrices/cases and custom macros are not supported in this implementation.
Unsupported or malformed formulas produce a question-specific export error;
they are not silently converted to wrong math or raw LaTeX. Existing question
sets can be re-exported without regenerating them. Previously downloaded PDFs
must be downloaded again.

## Deployment

After deploying the code, install only the PDF dependencies in the existing app
environment; do not reinstall the entire historical requirements file:

```bash
cd /opt/herlink
.venv/bin/python -m pip install -r requirements-pdf.txt
.venv/bin/python -m unittest discover -s tests -p 'test_pdf*.py'
systemctl restart herlink.service
```

Keep the bundled `fonts/` directory. Matplotlib includes the supporting math
fonts. No system LaTeX distribution, Node.js, Chromium, CDN, or AI call is used.
The Matplotlib import is lazy, so non-math exports still work without it. A math
export with missing dependencies gives an actionable error.

## Safety and layout

Input is escaped as text, not accepted as HTML. Formula images use generated
in-memory data URIs only. Mathtext never invokes TeX or a subprocess. External
file/link/image commands are rejected; errors do not contain parser paths or
the generated image payload. A process lock covers the renderer's font/parser
and rc state; each export has its own image cache. Mathematical operations are
not evaluated and the exporter does not correct a mathematically wrong question.

Exports are limited to 50 questions, 100,000 total characters, 20,000 per
question, 400 formula occurrences, 2,000 characters per formula, 40 nesting
levels and a 30-million-pixel per-export image budget. Oversized individual
formulas fail instead of generating giant or unreadably small images. Ordinary
questions stay intact across page boundaries; very long questions may split
with repeated headings. Fraction heights expand line spacing.

`tests/test_pdf_math.py` covers the reported calculus examples, image embedding,
Chinese text, delimiters, literal code/prices/HTML, malformed/unsupported input,
per-export caching/limits, parallel rendering, pagination, and the real endpoint
using an isolated Flask fixture. No production database, email or paid AI is used.
The full regression suite also passes with ReportLab 4.2.5 and Matplotlib 3.10.8
(105 passed, one skipped); this matches the server's ReportLab version.
