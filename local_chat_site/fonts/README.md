# Bundled Chinese PDF font

`NotoSansSC-Regular.ttf` is the regular (weight 400) static TrueType instance of
Noto Sans SC 2.004. It includes 30,890 Unicode mappings; no glyph subset was
removed from the upstream SC font. ReportLab embeds only the glyphs used by a
particular PDF, so exported files do not carry this entire 10.6 MB asset.

## Copyright and license

Copyright notice retained from the upstream font metadata:

> © 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'.

The font is distributed under SIL Open Font License 1.1; see `OFL.txt`.
The regular static instance retains the upstream `Noto Sans SC` family name
(not the reserved name `Source`). Keep this notice and `OFL.txt` with the font.

## Official source and integrity

- Repository: https://github.com/notofonts/noto-cjk
- Revision: `f8d157532fbfaeda587e826d4cd5b21a49186f7c`
- File: `Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf`
- Source URL: https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf
- Upstream Git blob (verified): `5371a543be5fc670c7cdee9760c03554ee3e9b8e`
- Source SHA-256: `d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964`
- Bundled static font SHA-256: `23a9fc0047b6ad5c6d34be65e219f6c49e1b0f1a7d89fc173c4f45c87e922a9f`

## Build and deploy

Generated once using fontTools 4.60.1:

```sh
python -m fontTools.varLib.instancer NotoSansSC-VF.ttf wght=400 --update-name-table -o NotoSansSC-Regular.ttf
```

This pins the variable font to a regular weight and removes variation tables
for compatibility with ReportLab. Rebuild timestamps can change the byte hash.
No fontTools build step is needed on the server. Deploy this entire directory
alongside `app.py` and `pdf_fonts.py`; do not copy Windows proprietary fonts.
Paths are independent of the process working directory and host OS.

If this font is absent or corrupt, PDF export fails with a clear message rather
than falling back to an unreadable Latin-only font. This fixes Chinese text;
LaTeX formula layout in PDF export is a separate feature.
