# SOOTS website

The website of SOOTS (Sustaining Roots Music), a Raleigh Charter High School community
project supporting Piedmont blues musicians since 2006.

- **Students editing the site:** read [docs/EDITING.md](docs/EDITING.md). No code needed.
- **Teacher or owner setting it up:** read [docs/SETUP.md](docs/SETUP.md).

## How it works

```
students edit in Pages CMS  ─►  content/ in this repository  ─►  GitHub Actions runs build.py  ─►  GitHub Pages
 (app.pagescms.org)              (text, photos, captions)          (.github/workflows/deploy.yml)     (the live site)
```

| Path | What it is |
|---|---|
| `content/site.json` | Menu, footer, email, social links |
| `content/home.json` | The home page |
| `content/pages/*.json` | One file per page (`cake-bake.json` → `cake-bake.html`) |
| `content/photos/`, `content/files/` | Photos and logos; audio, video and PDFs |
| `assets/css`, `assets/js` | The design (style sheet and scripts) |
| `build.py` | Turns `content/` into the finished site in `site/` |
| `.pages.yml` | What Pages CMS shows editors (fields, labels, help text) |
| `tools/check_editor_config.py` | Checks that `.pages.yml` covers every field in `content/` |

## Building on your own computer

```bash
pip install -r requirements.txt
python3 build.py
```

Then open `site/index.html` in a browser. Use `python3 build.py --names-sheet` to also write
`photo-names.html`, a printable sheet of artist photos that still need names in their captions.

## Changing the code

- **A new kind of field:** add it to `build.py`, to the matching entry in `.pages.yml`, then run
  `python3 tools/check_editor_config.py`. Pages CMS only shows fields listed in `.pages.yml`.
  GitHub runs the same check before every publish, and stops if a field is missing.
- **Special pages** (Events, Soil to Soul Series, Folk Projects…) have their own layout
  functions in `build.py` (`SPECIAL` near the end). Every other page uses the standard layout.
- The old Weebly site was copied into `original/` on the maintainer's computer. It isn't in this
  repository and isn't needed to build the site.
