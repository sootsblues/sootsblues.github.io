#!/usr/bin/env python3
"""Builds the SOOTS (Sustaining Roots Music) website.

Everything on the site comes from the files in content/:

    content/site.json       menu, footer, email address, social links
    content/home.json       the home page
    content/pages/*.json    one file per page (cake-bake.json becomes cake-bake.html)
    content/photos/         photos and logos
    content/files/          audio, video and PDF files

Students edit those files through Pages CMS (see README.md at the top of the repository). This script turns
them into the plain HTML/CSS/JS site in ./site, and GitHub runs it automatically after
every change (.github/workflows/deploy.yml). To build on your own computer:

    pip install -r requirements.txt
    python3 build.py                 build the site into ./site
    python3 build.py --names-sheet   also write photo-names.html, a printable list of
                                     artist photos that still need names in their captions
"""
import hashlib, html, json, os, re, shutil, sys
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
PHOTOS_DIR = os.path.join(CONTENT, "photos")
FILES_DIR = os.path.join(CONTENT, "files")
OUT = os.path.join(ROOT, "site")

def esc(s, quote=True):
    """Escape text for HTML. Emptied fields (None) become empty text."""
    return html.escape("" if s is None else str(s), quote)

# ================================================================ reading content
WARNINGS = []

def warn(msg):
    WARNINGS.append(msg)
    print("  ! " + msg)

def load(path):
    rel = os.path.relpath(path, ROOT)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"\nBUILD STOPPED: {rel} is missing. It holds part of the site, so put it back.")
    except json.JSONDecodeError as e:
        sys.exit(f"\nBUILD STOPPED: {rel} has a typo (line {e.lineno}, column {e.colno}: {e.msg}).\n"
                 "This usually comes from editing the file by hand on GitHub. Undo that change, or use Pages CMS instead.")
    if not isinstance(data, dict):
        sys.exit(f"\nBUILD STOPPED: {rel} should hold a set of fields ({{...}}), but it holds something else.")
    return data

SITE = load(os.path.join(CONTENT, "site.json"))
HOME = load(os.path.join(CONTENT, "home.json"))
PAGES_DIR = os.path.join(CONTENT, "pages")
PAGES = {}
for _f in sorted(os.listdir(PAGES_DIR)):
    if _f.endswith(".json"):
        _slug = re.sub(r"[^a-z0-9]+", "-", _f[:-5].lower()).strip("-") or "page"
        if _slug != _f[:-5]:
            warn(f"content/pages/{_f}: web addresses use lowercase letters, numbers and dashes, so this page is at {_slug}.html")
        if _slug + ".html" in PAGES:
            warn(f"content/pages/{_f}: another page already uses the address {_slug}.html, so this one was skipped")
            continue
        PAGES[_slug + ".html"] = load(os.path.join(PAGES_DIR, _f))
for _page, _d in PAGES.items():
    if not (_d.get("title") or "").strip():
        _d["title"] = _page[:-5].replace("-", " ").title()
        warn(f"content/pages/{_page[:-5]}.json has no title, so it is shown as “{_d['title']}”")

# changes whenever the CSS or JS changes, so browsers fetch the new files instead of a cached copy
ASSET_VERSION = hashlib.md5(b"".join(open(os.path.join(ROOT, "assets", d, f), "rb").read()
                                      for d, f in (("css", "style.css"), ("js", "site.js")))).hexdigest()[:8]
SITE_URL = (SITE.get("site_url") or "https://www.sootsblues.org/").rstrip("/") + "/"
EMAIL = SITE.get("email", "")

def get(d, *keys, default=""):
    """Nested lookup that tolerates missing or empty fields."""
    for k in keys:
        d = d.get(k) if isinstance(d, dict) else None
        if d is None:
            return default
    return d

def stored_path(ref, folder):
    """A photo or file as the editor saves it ('/photos/x.jpg', 'photos/x.jpg',
    'content/photos/x.jpg' or just 'x.jpg') -> its path inside content/<folder>."""
    r = (ref or "").strip().split("?")[0].lstrip("/")
    for prefix in (f"content/{folder}/", f"{folder}/"):
        if r.startswith(prefix):
            return r[len(prefix):]
    return r

def P(ref):
    return stored_path(ref, "photos")

def F(ref):
    return stored_path(ref, "files")

# ================================================================ site map
NAV = [(m.get("label", ""), m.get("link", ""), P(m.get("feature_image")),
        [(k.get("label", ""), k.get("link", ""), 1 if k.get("indent") else 0) for k in m.get("items") or []])
       for m in SITE.get("menu") or []]
PARENT = {}
for label, h, _, kids in NAV:
    PARENT[h] = (label, h)
    for kl, kh, _ in kids:
        PARENT.setdefault(kh, (label, h))
for _page, _d in PAGES.items():  # pages that are not in the menu say which menu item they belong under
    if _page not in PARENT and _d.get("menu_section"):
        for label, h, _, _ in NAV:
            if label == _d["menu_section"]:
                PARENT[_page] = (label, h)
SIBLINGS = {s["name"]: s.get("pages") or [] for s in SITE.get("sections") or [] if s.get("name")}

def group_of(page):
    for g, pages in SIBLINGS.items():
        if page in pages:
            return g
    if page == "in-the-field.html":  # In the Field shows the Folk Projects list
        return "folk"
    return None

def title_of(page):
    return PAGES[page]["title"]

# ================================================================ images
IMG_DIR = os.path.join(OUT, "img")
FULL_DIR = os.path.join(IMG_DIR, "full")
_img_cache = {}

def norm(name):
    return re.sub(r"_(orig|med|large|small)(?=\.)", "", name)

def stem_of(name):
    return re.sub(r"_(orig|med|large|small)$", "", os.path.splitext(os.path.basename(name))[0])

def find_src(name):
    if not name:
        return None
    p = os.path.join(PHOTOS_DIR, name)
    if os.path.isfile(p):
        return p
    folder = os.path.dirname(p)
    base = norm(os.path.basename(name))
    if os.path.isdir(folder):
        for cand in os.listdir(folder):
            if norm(cand) == base:
                return os.path.join(folder, cand)
    return None

def img(name, max_w=1600):
    """Return (display_url, full_url, w, h) for a photo in content/photos."""
    key = (name, max_w)
    if key in _img_cache:
        return _img_cache[key]
    src = find_src(name)
    if not src:
        warn(f"photo not found: content/photos/{name} (used on {CUR['page'] or 'the site'}). It was left out")
        _img_cache[key] = None
        return None
    rel = os.path.relpath(src, PHOTOS_DIR)
    stem = re.sub(r"[^a-z0-9-]+", "-", os.path.splitext(norm(rel))[0].lower()).strip("-")
    try:
        im = ImageOps.exif_transpose(Image.open(src))
    except Exception:
        warn(f"content/photos/{rel} could not be opened as a picture (used on {CUR['page'] or 'the site'}). It was left out")
        _img_cache[key] = None
        return None
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    ext = ".png" if has_alpha else ".jpg"
    w, h = im.size
    out_name = f"{stem}-{max_w}{ext}"
    out_path = os.path.join(IMG_DIR, out_name)
    if not os.path.exists(out_path):
        disp = im.copy()
        if w > max_w:
            disp = disp.resize((max_w, round(h * max_w / w)), Image.LANCZOS)
        if has_alpha:
            disp.save(out_path, optimize=True)
        else:
            disp.convert("RGB").save(out_path, quality=82, optimize=True, progressive=True)
    dw, dh = (min(w, max_w), round(h * min(w, max_w) / w))
    full_url = "img/" + out_name
    if w > max_w:
        fname = stem + "-full" + ext
        fpath = os.path.join(FULL_DIR, fname)
        if not os.path.exists(fpath):
            if has_alpha:
                im.save(fpath, optimize=True)
            else:
                big = im if w <= 3000 else im.resize((3000, round(h * 3000 / w)), Image.LANCZOS)
                big.convert("RGB").save(fpath, quality=88, optimize=True, progressive=True)
        full_url = "img/full/" + fname
    res = ("img/" + out_name, full_url, dw, dh)
    _img_cache[key] = res
    return res

def media(name):
    """Copy an audio/video/PDF file from content/files into the site; return its address."""
    src = os.path.join(FILES_DIR, name)
    dst = os.path.join(OUT, "media", name)
    if not os.path.isfile(src):
        warn(f"file not found: content/files/{name} (used on {CUR['page'] or 'the site'})")
    elif not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    return "media/" + name

# ================================================================ text helpers
def plain(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()

def fix_links(h):
    h = re.sub(r'href="(?:https?://(?:www\.)?sootsblues\.org)?/([a-z0-9-]+\.html)"', r'href="\1"', h)
    h = re.sub(r'href="(?:https?://(?:www\.)?sootsblues\.org)?/"', 'href="index.html"', h)
    h = re.sub(r'href="/(?:content/)?files/([^"]+)"', lambda m: f'href="{media(m.group(1))}"', h)
    h = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', h)
    return h.replace('<a href=""', "<a")

def href(u):
    if not u or u.startswith("javascript"):
        return None
    if re.match(r"/?(content/)?files/", u):
        return media(F(u))
    if u.startswith("/"):
        return u.lstrip("/") or "index.html"
    return u

def para(h, page=""):
    """Page text -> paragraphs and subheads.

    Text saved by Pages CMS is already in paragraphs and is used as is (a paragraph
    starting with a bold "Q:" becomes an interview question). Older text that is one
    long run of lines split by <br/> is cut into paragraphs, and short "Heading:" lines
    become subheads."""
    h = h or ""
    if re.search(r"<(p|h[1-6]|ul|ol|blockquote)[\s>]", h):
        h = fix_links(h).replace("\xa0", " ")
        h = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r'<h3 class="subhead">\1</h3>', h, flags=re.S)
        h = re.sub(r"<p>\s*<strong>Q:</strong>\s*(.*?)</p>", r'<p class="qa-q"><span>Q</span>\1</p>', h, flags=re.S)
        h = re.sub(r"<p[^>]*>(\s|&nbsp;|<br\s*/?>)*</p>", "", h)
        return h.strip()
    h = fix_links(h).replace("\xa0", " ")
    # Weebly authors indented paragraphs with runs of spaces inside one line
    h = re.sub(r"\s{6,}(?=[A-Z“\"])", "<br/><br/>", h)
    lines = re.split(r"\s*<br/>\s*", h)
    out, buf = [], []

    def flush():
        if buf:
            p = "<br/>".join(buf).strip()
            if plain(p):
                out.append(("p", p))
            buf.clear()

    for ln in lines:
        t = plain(ln)
        if not t:
            flush()
            continue
        if len(t) < 48 and t.endswith(":") and not t.lower().startswith(("http", "by")):
            flush()
            out.append(("h", t.rstrip(":").strip()))
            continue
        if re.fullmatch(r"\s*<strong>.*</strong>\s*", ln, re.S) and len(t) < 90 and not buf:
            flush()
            out.append(("h", t.rstrip(":").strip()))
            continue
        if page == "interviews.html" and t.endswith("?") and len(t) < 160:
            flush()
            out.append(("q", t))
            continue
        if page == "interviews.html" and t.lower().startswith("interview conducted"):
            flush()
            out.append(("meta", t))
            continue
        if page == "interviews.html" and t.lower().startswith("interview with"):
            flush()
            out.append(("h", t))
            continue
        if buf and len(plain(buf[-1])) > 70 and re.search(r"[.!?\"”’)]\s*(</\w+>)?$", buf[-1].strip()):
            flush()
        buf.append(ln.strip())
    flush()
    html_out = []
    for kind, v in out:
        if kind == "p":
            html_out.append(f"<p>{v}</p>")
        elif kind == "h":
            html_out.append(f'<h3 class="subhead">{esc(v)}</h3>')
        elif kind == "q":
            html_out.append(f'<p class="qa-q"><span>Q</span>{esc(v)}</p>')
        elif kind == "meta":
            html_out.append(f'<p class="meta">{esc(v)}</p>')
    return "\n".join(html_out)

ORN = '<div class="orn" aria-hidden="true"><svg viewBox="0 0 120 16"><path d="M0 8h46M74 8h46" stroke="currentColor" stroke-width="1"/><path d="M60 2l6 6-6 6-6-6z" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="50" cy="8" r="1.6" fill="currentColor"/><circle cx="70" cy="8" r="1.6" fill="currentColor"/></svg></div>'

# ================================================================ components
PHOTOS = []  # (page, photo, caption, image url) for every photo shown; used by --names-sheet
CUR = {"page": None}  # page being built

def figure(name, cap="", link=None, cls="", max_w=1600):
    r = img(name, max_w)
    if not r:
        return ""
    d, full, w, h = r
    cap = (cap or "").strip()
    if not link:
        PHOTOS.append((CUR["page"], name, cap, d))
    alt = esc(cap)
    tag = f'<img src="{d}" width="{w}" height="{h}" alt="{alt}" loading="lazy" decoding="async">'
    link = href(link) if link else None
    if link:
        ext = ' target="_blank" rel="noopener"' if link.startswith("http") else ""
        play = '<span class="play" aria-hidden="true"></span><span class="fig-tag">Watch on YouTube</span>' if "youtube" in link else ""
        inner = f'<a href="{esc(link)}"{ext} class="fig-link">{tag}{play}</a>'
    else:
        inner = f'<a href="{full}" class="lb" data-cap="{alt}">{tag}</a>'
    capt = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return f'<figure class="fig reveal {cls}">{inner}{capt}</figure>'

def year_tag(name):
    m = re.search(r"(20[012]\d)", name)
    return m.group(1) if m else "More"

def photo_list(items):
    """[{"image": ..., "caption": ...}] from the editor -> [(photo, caption)]."""
    return [(P(x.get("image")), (x.get("caption") or "").strip()) for x in items or [] if isinstance(x, dict) and x.get("image")]

def gallery(items, kind="grid", filters=False, polaroid=False):
    figs, tags = [], []
    for name, cap in items:
        r = img(name, 1200)
        if not r:
            continue
        d, full, w, h = r
        PHOTOS.append((CUR["page"], name, cap, d))
        tag = year_tag(name) if filters else ""
        if tag and tag not in tags:
            tags.append(tag)
        figs.append(
            f'<figure class="g-item{" polaroid" if polaroid else ""}"{f" data-tag={chr(34)}{tag}{chr(34)}" if tag else ""}>'
            f'<a href="{full}" class="lb" data-cap="{esc(cap)}">'
            f'<img src="{d}" width="{w}" height="{h}" alt="{esc(cap)}" loading="lazy" decoding="async"></a>'
            + (f"<figcaption>{esc(cap)}</figcaption>" if cap else "") + "</figure>")
    chips = ""
    if filters and len(tags) > 2:
        tags = sorted([t for t in tags if t != "More"]) + (["More"] if "More" in tags else [])
        chips = ('<div class="chips" role="toolbar" aria-label="Filter photos by year"><button class="chip on" data-filter="all">All</button>'
                 + "".join(f'<button class="chip" data-filter="{t}">{t}</button>' for t in tags) + "</div>")
    more = ""
    collapsed = ""
    if len(figs) > 12:
        collapsed = " collapsed"
        more = f'<div class="more-row"><button class="btn btn-ghost show-more">Show all {len(figs)} photos<span class="arr" aria-hidden="true">↓</span></button></div>'
    return f'<div class="filterable{collapsed}">{chips}<div class="gallery {kind}">' + "".join(figs) + f"</div>{more}</div>"

def button(label, link, i=0):
    u = href(link)
    if not u:
        return f'<span class="btn btn-disabled" aria-disabled="true">{esc(label)} · coming soon</span>'
    ext = ' target="_blank" rel="noopener"' if u.startswith("http") else ""
    return f'<a class="{"btn" if i == 0 else "btn btn-ghost"}" href="{esc(u)}"{ext}>{esc(label)}<span class="arr" aria-hidden="true">→</span></a>'

def iframe(src):
    src = (src or "").strip()
    if "generateMap" in src or src == "map":
        return ('<div class="embed map"><iframe title="Map: Raleigh Charter High School" loading="lazy" '
                'src="https://maps.google.com/maps?q=35.7960187,-78.6472534&z=15&output=embed"></iframe></div>')
    if src.startswith("//"):
        src = "https:" + src
    m = re.match(r"https?://(?:www\.)?(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]+)", src)
    if m:  # a normal YouTube page address pasted into the editor
        src = f"https://www.youtube.com/embed/{m.group(1)}"
    if "youtube" in src:
        return f'<div class="embed video reveal"><iframe title="Video" loading="lazy" src="{esc(src.split("?")[0])}" allowfullscreen></iframe></div>'
    if "soundcloud" in src:
        src = re.sub(r"color=%23[0-9a-f]{6}", "color=%239c4426", src)
        return f'<div class="embed sc{" tall" if "playlists" in src else ""} reveal"><iframe title="SoundCloud player" loading="lazy" src="{esc(src)}"></iframe></div>'
    if src:
        warn(f"an embed on {CUR['page']} is not a YouTube or SoundCloud address, so it was left out: {src}")
    return ""

def player(name, title="", sub=""):
    """Vinyl-record audio player (custom controls, see site.js)."""
    u = media(name)
    t, s = (title or "Listen"), (sub or "")
    return f'''<div class="player reveal" data-src="{u}">
  <button class="pl-disc" aria-label="Play {esc(t)}"><span class="vinyl"><span class="label"><img src="img/logo-badge.png" alt=""></span></span><span class="pl-icon" aria-hidden="true"></span></button>
  <div class="pl-body"><span class="pl-kicker">Listen</span><span class="pl-title">{esc(t)}</span>{f'<span class="pl-sub">{esc(s)}</span>' if s else ""}
    <div class="pl-track"><input class="pl-seek" type="range" min="0" max="1000" value="0" aria-label="Seek"><span class="pl-time">0:00</span></div></div>
  <audio preload="none" src="{u}"></audio>
</div>'''

def video(name, poster=None):
    u = media(name)
    p = f' poster="{img(poster)[0]}"' if poster and find_src(poster) else ""
    return f'<div class="embed video reveal"><video controls preload="none" playsinline{p} src="{u}"></video></div>'

def logo(name, link, title=""):
    r = img(name, 600)
    if not r:
        return ""
    tag = f'<img src="{r[0]}" width="{r[2]}" height="{r[3]}" alt="{esc(title)}" loading="lazy">'
    if link:
        return f'<a class="logo-cell" href="{esc(link)}" target="_blank" rel="noopener">{tag}</a>'
    return f'<span class="logo-cell">{tag}</span>'

def bibliography(items):
    lis = "".join(f"<li>{fix_links(re.sub(r'(https?://[^ ]+?)(?=\\.?$)', lambda m: f'<a href={chr(34)}{m.group(1)}{chr(34)}>{m.group(1)}</a>', esc(i)))}</li>"
                  for i in items or [] if i)
    return f'<details class="biblio"><summary>Bibliography</summary><ul>{lis}</ul></details>' if lis else ""

def render(blocks, page, depth=0):
    """Page sections from the editor -> HTML."""
    out = []
    i = 0
    blocks = [b for b in blocks or [] if isinstance(b, dict)]
    while i < len(blocks):
        b = blocks[i]
        t = b.get("type")
        if t == "heading":
            txt = (b.get("text") or "").strip().rstrip(":").strip()
            if txt and txt.lower() != title_of(page).lower():
                out.append(f'<h2 class="reveal">{esc(txt)}</h2>' if depth == 0 else f'<h3 class="subhead">{esc(txt)}</h3>')
        elif t == "text":
            out.append(para(b.get("body"), page))
        elif t == "photo":
            if b.get("image"):
                out.append(figure(P(b["image"]), b.get("caption"), b.get("link") or None))
        elif t == "gallery":
            out.append(gallery(photo_list(b.get("photos")), "grid"))
        elif t == "button":
            row = []
            while i < len(blocks) and blocks[i].get("type") == "button":
                row.append(button(blocks[i].get("label") or "", blocks[i].get("link"), len(row)))
                i += 1
            out.append('<div class="btn-row">' + "".join(row) + "</div>")
            continue
        elif t == "embed":
            out.append(iframe(b.get("url")))
        elif t == "audio":
            if b.get("file"):
                out.append(player(F(b["file"]), b.get("title"), b.get("subtitle")))
        elif t == "video":
            if b.get("file"):
                out.append(video(F(b["file"]), P(b.get("poster"))))
        elif t == "contact_form":
            out.append(CONTACT_FORM)
        elif t == "bibliography":
            out.append(bibliography(b.get("items")))
        elif t == "columns":
            cols = [h for h in (render(c.get("blocks"), page, depth + 1) for c in b.get("columns") or [] if isinstance(c, dict)) if h.strip()]
            if len(cols) == 1:
                out.append(cols[0])
            elif cols:
                out.append(f'<div class="cols cols-{len(cols)}">' + "".join(f'<div class="col">{h}</div>' for h in cols) + "</div>")
        else:
            warn(f"{page}: a section of an unknown kind ({t}) was left out")
        i += 1
    return "\n".join(o for o in out if o)

CONTACT_FORM = f'''
<form class="contact-form" id="contact-form" novalidate>
  <div class="field-row">
    <label>First name<input name="first" autocomplete="given-name" required></label>
    <label>Last name<input name="last" autocomplete="family-name"></label>
  </div>
  <label>Email<input type="email" name="email" autocomplete="email" required></label>
  <label>Message<textarea name="message" rows="6" required></textarea></label>
  <button class="btn" type="submit">Send message<span class="arr" aria-hidden="true">→</span></button>
  <p class="form-note">Opens your email app with the message ready to send to {EMAIL}.</p>
</form>'''

# ================================================================ layout
ICONS = {
    "Instagram": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="17.3" cy="6.7" r="1.1" fill="currentColor"/></svg>',
    "Facebook": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 8h3V4.5h-3c-2.5 0-4 1.6-4 4V11H7.5v3.5H10V21h3.5v-6.5h3l.5-3.5h-3.5V8.8c0-.5.3-.8.5-.8Z" fill="currentColor"/></svg>',
    "YouTube": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="5.5" width="19" height="13" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 9.2v5.6l5-2.8-5-2.8Z" fill="currentColor"/></svg>',
    "Mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5.5" width="18" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m3.5 6.5 8.5 7 8.5-7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
    "Link": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
}
SOCIAL = [(s.get("name", ""), s.get("url", ""), s.get("handle", "")) for s in SITE.get("social") or [] if s.get("url")]

def icon(name):
    return ICONS.get(name, ICONS["Link"])

def nav_html(page):
    cur = PARENT.get(page, (None, None))[1]
    items = []
    for label, h, feat, kids in NAV:
        active = ' aria-current="true"' if h == cur else ""
        if not kids:
            items.append(f'<li><a href="{h}" class="top"{active}>{esc(label)}</a></li>')
            continue
        links = "".join(
            f'<li class="{"indent" if ind else ""}"><a href="{kh}"{" aria-current=page" if kh == page else ""}>'
            f'<span class="ml">{esc(kl)}</span></a></li>'
            for kl, kh, ind in kids)
        r = img(feat, 600) if feat else None
        fimg = r[0] if r else ""
        items.append(
            f'<li class="has-sub"><a href="{h}" class="top"{active}>{esc(label)}</a>'
            f'<button class="sub-toggle" aria-expanded="false" aria-label="Show {esc(label)} pages"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></button>'
            f'<div class="mega"><div class="mega-inner">'
            f'<div class="mega-intro"><p class="mega-title">{esc(label)}</p></div>'
            f'<ul class="mega-links{" two" if len(kids) > 5 else ""}">{links}</ul>'
            f'<a class="mega-feat" href="{h}" tabindex="-1" aria-hidden="true"><img src="{fimg}" alt="" loading="lazy"><span class="tape" aria-hidden="true"></span></a>'
            f'</div></div></li>')
    return "".join(items)

def head(title, desc, page):
    full_title = "SOOTS · Sustaining Roots Music" if page == "index.html" else f"{title} · SOOTS Blues"
    canon = SITE_URL + ("" if page == "index.html" else page)
    base = '\n<base href="/">' if page == "404.html" else ""
    donate = SITE.get("donate_button") or {}
    donate_html = (f'<li class="nav-cta"><a class="btn btn-small" href="{esc(donate["link"])}">{esc(donate.get("label") or "Donate")}</a></li>'
                   if donate.get("link") else "")
    return f'''<!doctype html>
<html lang="en" class="no-js">
<head>{base}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE_URL}img/og.jpg">
<meta property="og:url" content="{canon}">
<meta name="theme-color" content="#1f1b16">
<link rel="canonical" href="{canon}">
<link rel="icon" href="img/favicon.png">
<script>document.documentElement.classList.replace("no-js","js")</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Courier+Prime:wght@400;700&family=DM+Serif+Display:ital@0;1&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/style.css?v={ASSET_VERSION}">
<script src="js/site.js?v={ASSET_VERSION}" defer></script>
</head>
<body class="page-{page.replace('.html', '')}">
<a class="skip" href="#main">Skip to content</a>
<div class="progress" aria-hidden="true"></div>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="index.html" aria-label="SOOTS home">
      <img src="img/logo-badge.png" width="52" height="52" alt="">
      <span class="brand-text"><span class="brand-name">SOOTS</span><span class="brand-sub">Sustaining Roots Music</span></span>
    </a>
    <button class="menu-toggle" aria-expanded="false" aria-controls="site-nav"><span class="bars" aria-hidden="true"></span><span class="menu-label">Menu</span></button>
    <nav id="site-nav" class="site-nav" aria-label="Main">
      <ul>{nav_html(page)}{donate_html}</ul>
    </nav>
  </div>
</header>
<main id="main">
'''

def foot():
    soc = "".join(f'<a href="{u}" target="_blank" rel="noopener" aria-label="{k}">{icon(k)}</a>' for k, u, _ in SOCIAL)
    cols = "".join(
        f'<div><h4>{esc(l)}</h4><ul>' + "".join(
            f'<li><a href="{kh}">{esc(kl)}</a></li>' for kl, kh, ind in (kids or [(l, h, 0)]) if not ind) + "</ul></div>"
        for l, h, _, kids in NAV)
    f = SITE.get("footer") or {}
    return f'''</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div class="footer-brand">
      <img class="footer-disc" src="img/logo-badge-light.png" width="120" height="120" alt="SOOTS record-label logo">
      <p>{esc(f.get("about", ""))}</p>
      <p class="footer-contact"><a href="mailto:{EMAIL}">{ICONS["Mail"]}{EMAIL}</a></p>
      <div class="social">{soc}</div>
    </div>
    <div class="footer-links">{cols}</div>
  </div>
  <div class="wrap footer-base"><span>{esc(f.get("copyright", ""))}</span><span class="footer-groove">{esc(f.get("tagline", ""))}</span></div>
</footer>
<button class="to-top" aria-label="Back to top"><svg viewBox="0 0 40 40" aria-hidden="true"><circle class="ring-bg" cx="20" cy="20" r="18"/><circle class="ring" cx="20" cy="20" r="18"/><path d="M14 22l6-6 6 6" fill="none" stroke="currentColor" stroke-width="1.8"/></svg></button>
<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" aria-label="Photo viewer">
  <button class="lb-close" aria-label="Close">×</button>
  <button class="lb-prev" aria-label="Previous">‹</button>
  <figure><img alt=""><figcaption></figcaption></figure>
  <button class="lb-next" aria-label="Next">›</button>
  <span class="lb-count"></span>
</div>
</body>
</html>'''

def first_text(blocks):
    for b in blocks or []:
        for bb in ([b] if b.get("type") != "columns" else [x for c in b.get("columns") or [] for x in c.get("blocks") or []]):
            if bb.get("type") == "text" and len(plain(bb.get("body") or "")) > 60:
                t = plain(bb["body"])
                return (t[:155].rsplit(" ", 1)[0] + "…") if len(t) > 155 else t
    return ""

def description(page):
    d = PAGES[page]
    return (d.get("description") or d.get("subtitle") or first_text(d.get("blocks"))
            or SITE.get("default_description") or "")

def hero(page):
    data = PAGES[page]
    title = title_of(page)
    par = PARENT.get(page)
    kicker = data.get("kicker") or (par[0] if par and par[1] != page else "SOOTS")
    bg, vid = P(data.get("banner_image")), F(data.get("banner_video"))
    media_html = ""
    if vid:
        poster = img(os.path.splitext(vid)[0] + ".jpg") if find_src(os.path.splitext(vid)[0] + ".jpg") else None
        media_html = (f'<video class="hero-media" autoplay muted loop playsinline preload="metadata"'
                      f'{" poster=" + chr(34) + poster[0] + chr(34) if poster else ""} src="{media(vid)}"></video>')
    elif bg:
        r = img(bg, 2000)
        if r:
            media_html = f'<img class="hero-media" src="{r[0]}" alt="" fetchpriority="high">'
    crumbs = ""
    if par and par[1] != page:
        crumbs = f'<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span>/</span><a href="{par[1]}">{esc(par[0])}</a></nav>'
    elif page != "index.html":
        crumbs = '<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a></nav>'
    dek = data.get("subtitle")
    return f'''<section class="page-hero{" has-media" if media_html else ""}">
  {media_html}
  <div class="wrap hero-inner">
    {crumbs}
    <p class="kicker">{esc(kicker)}</p>
    <h1 class="hero-title">{esc(title)}</h1>
    {f'<p class="hero-dek">{esc(dek)}</p>' if dek else ""}
  </div>
  <div class="tear" aria-hidden="true"></div>
</section>'''

def sidebar_photo(page):
    s = PAGES[page].get("sidebar_photo") or {}
    return (P(s.get("image")), (s.get("caption") or "").strip()) if s.get("image") else (None, "")

def aside(page, photo=None, cap=""):
    parts = []
    facts = [(f.get("label", ""), f.get("value", "")) for f in PAGES[page].get("facts") or [] if f.get("label") or f.get("value")]
    if facts:
        rows = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in facts)
        parts.append(f'<div class="glance"><p class="glance-head">At a glance</p><dl>{rows}</dl></div>')
    if photo:
        r = img(photo, 900)
        if r:
            PHOTOS.append((CUR["page"], photo, cap, r[0]))
            parts.append(f'<a class="aside-photo lb" href="{r[1]}" data-cap="{esc(cap)}"><img src="{r[0]}" alt="{esc(cap)}" loading="lazy"><span class="tape" aria-hidden="true"></span></a>'
                         + (f'<p class="aside-cap">{esc(cap)}</p>' if cap else ""))
    g = group_of(page)
    if g:
        links = "".join(
            f'<li><a href="{p}"{" aria-current=page" if p == page else ""}>{esc(title_of(p))}</a></li>'
            for p in SIBLINGS[g] if p in PAGES)
        parts.append(f'<nav class="section-nav" aria-label="In this section"><p class="glance-head">In this section</p><ul>{links}</ul></nav>')
    return '<aside class="rail">' + "".join(parts) + "</aside>" if parts else ""

def page_aside(page):
    photo, cap = sidebar_photo(page)
    return aside(page, photo, cap)

def pager(page):
    g = group_of(page)
    if not g or page not in SIBLINGS[g]:
        return ""
    lst = [p for p in SIBLINGS[g] if p in PAGES]
    i = lst.index(page)
    prev_p, next_p = (lst[i - 1] if i > 0 else None), (lst[i + 1] if i < len(lst) - 1 else None)
    def card(p, d):
        if not p:
            return "<span></span>"
        return (f'<a class="pg-{d}" href="{p}"><span class="kicker">{"← Previous" if d == "prev" else "Next →"}</span>'
                f'<span class="pg-title">{esc(title_of(p))}</span></a>')
    return f'<nav class="wrap pager" aria-label="More in this section">{card(prev_p, "prev")}{card(next_p, "next")}</nav>'

def insert_quote(body, page):
    pq = PAGES[page].get("pull_quote") or {}
    q = (pq.get("text") or "").strip()
    if not q or q.lower()[:30] not in plain(body).lower().replace("’", "'").replace("'", "'") and q.lower()[:30] not in plain(body).lower():
        return body
    by = pq.get("by")
    block = (f'<blockquote class="pull reveal"><p>{esc(q.rstrip("."))}.</p>'
             + (f"<cite>{esc(by)}</cite>" if by else "") + "</blockquote>")
    idx = [m.end() for m in re.finditer(r"</p>", body)]
    try:
        nth = int(pq.get("after_paragraph") or 1)
    except (TypeError, ValueError):
        nth = 1
    pos = idx[nth] if len(idx) > nth + 1 else (idx[0] if idx else 0)
    return body[:pos] + block + body[pos:]

def article(page, extra_after=""):
    """Two-column story layout: prose + sticky rail. Big galleries break out full width."""
    blocks = [b for b in PAGES[page].get("blocks") or [] if isinstance(b, dict)]
    bib = [b for b in blocks if b.get("type") == "bibliography"]
    main_b, wide = [], []
    for b in blocks:
        if b.get("type") == "bibliography":
            continue
        if b.get("type") == "gallery" and len(photo_list(b.get("photos"))) >= 4:
            wide.append(b)
        else:
            main_b.append(b)
    body = render(main_b, page)
    body = re.sub(r"<p>", '<p class="dropcap">', body, count=1) if len(plain(body)) > 400 else body
    body = insert_quote(body, page)
    body += "".join(bibliography(b.get("items")) for b in bib)
    photo, cap = sidebar_photo(page)
    if not photo:
        for b in blocks:
            if b.get("type") == "gallery" and photo_list(b.get("photos")):
                photo, cap = photo_list(b.get("photos"))[0]
                break
    out = f'<div class="wrap article"><div class="prose story">{body}</div>{aside(page, photo, cap)}</div>'
    for g in wide:
        out += (f'<section class="wrap wide-gallery">{ORN}<div class="section-head center"><h2 class="scribble">Photographs</h2></div>'
                + gallery(photo_list(g.get("photos")), "grid", filters=(page == "cake-bake.html"), polaroid=True) + "</section>")
    return out + extra_after

# ================================================================ special pages
def body_social(page):
    d = PAGES[page]
    cards = "".join(
        f'<a class="social-card tilt" href="{u}" target="_blank" rel="noopener">{icon(k)}<span class="sc-name">{esc(k)}</span>'
        f'<span class="sc-handle">{esc(h)}</span><span class="arr" aria-hidden="true">↗</span></a>'
        for k, u, h in SOCIAL)
    return f'<section class="wrap block"><div class="section-head center reveal"><h2 class="scribble">{esc(d.get("heading", ""))}</h2></div><div class="social-cards">{cards}</div></section>'

def body_contact(page):
    d = PAGES[page]
    rows = "".join(f'<li><span class="kicker">{esc(m.get("label", ""))}</span><a href="mailto:{esc(m["address"])}">{esc(m["address"])}</a></li>'
                   for m in d.get("emails") or [] if m.get("address"))
    soc = "".join(f'<a href="{u}" target="_blank" rel="noopener" aria-label="{k}">{icon(k)}</a>' for k, u, _ in SOCIAL)
    addr = "<br>".join(esc(l) for l in (d.get("address") or "").splitlines() if l.strip())
    intro = d.get("intro") or ""
    # the editor wraps text in <p>; a paragraph can't sit inside another paragraph
    lede = f'<div class="lede">{intro}</div>' if re.search(r"<(p|ul|ol)[\s>]", intro) else f'<p class="lede">{intro}</p>'
    return f'''<section class="wrap block contact-grid">
  <div><h2 class="reveal scribble">{esc(d.get("heading", ""))}</h2>{lede}{CONTACT_FORM}</div>
  <aside class="contact-card"><ul class="mail-list">{rows}</ul>
    <p class="addr">{addr}</p>
    {iframe("map") if d.get("show_map") else ""}<div class="social dark">{soc}</div></aside>
</section>'''

def body_donations(page):
    d = PAGES[page]
    cards = []
    for n, c in enumerate(d.get("cards") or [], 1):
        items = [f'<p>{esc(it.get("text", ""))}</p>' + (button(it.get("button_label") or "", it.get("button_link"), i) if it.get("button_label") else "")
                 for i, it in enumerate(it for it in c.get("items") or [] if it.get("text") or it.get("button_label"))]
        r = img(P(c.get("photo")), 700) if c.get("photo") else None
        if r:
            items.append(f'<figure class="scrap"><img src="{r[0]}" alt="" loading="lazy"><span class="tape" aria-hidden="true"></span></figure>')
        cards.append(f'<article class="give-card reveal"><span class="give-no">{n:02d}</span><h3>{esc(c.get("title", ""))}</h3>'
                     + "\n    ".join(items) + "</article>")
    return f'''<section class="wrap block"><div class="section-head center reveal"><h2 class="scribble">{esc(d.get("heading", ""))}</h2>
<p class="lede narrow-text">{esc(d.get("intro", ""))}</p></div>
<div class="give-grid two">
  {(chr(10) + "  ").join(cards)}
</div></section>'''

def ticket(e):
    r = img(P(e.get("image")), 900)
    pos = e.get("part_of_speech")
    word = f'{esc(e.get("name", ""))} <em>({esc(pos)})</em>' if pos else esc(e.get("name", ""))
    return f'''<a class="ticket tilt reveal" href="{esc(e.get("page", ""))}">
  <span class="t-img"><img src="{r[0] if r else ""}" alt="" loading="lazy"></span>
  <span class="t-body"><span class="t-word">{word}</span><span class="t-def">{esc(e.get("definition", ""))}</span><span class="t-more">Learn more →</span></span>
  <span class="t-stub"><span>{esc(e.get("stub_top", ""))}</span><b>Admit<br>One</b><span>{esc(e.get("stub_bottom", ""))}</span></span>
</a>'''

def body_events(page):
    tix = "".join(ticket(e) for e in PAGES[page].get("events") or [])
    return f'<section class="wrap block"><div class="tickets">{tix}</div></section>'

def episodes():
    return PAGES.get("soil-to-soul-series.html", {}).get("episodes") or []

def sleeve(e):
    r = img(P(e.get("image")), 800)
    sub = e.get("subtitle")
    return f'''<a class="sleeve-card reveal" href="{esc(e.get("page", ""))}">
  <span class="sleeve"><span class="disc" aria-hidden="true"><span class="label"><img src="img/logo-badge.png" alt=""></span></span>
    <span class="cover"><img src="{r[0] if r else ""}" alt="" loading="lazy"></span></span>
  <span class="sl-no">Episode {esc(e.get("number", ""))}</span><span class="sl-title">{esc(e.get("title", ""))}</span>{f'<span class="sl-sub">{esc(sub)}</span>' if sub else ""}
</a>'''

def body_soil(page):
    intro = PAGES[page].get("intro") or ""
    sl = "".join(sleeve(e) for e in episodes())
    return f'''<div class="wrap article narrow"><div class="prose story">{re.sub("<p>", '<p class="dropcap">', intro, count=1)}</div>{page_aside(page)}</div>
<section class="band stitched"><div class="wrap"><div class="sleeves">{sl}</div></div></section>'''

def body_folk(page):
    d = PAGES[page]
    items = []
    for e in d.get("projects") or []:
        r = img(P(e.get("image")), 700) if e.get("image") else None
        btn = ('<div class="btn-row">' + button(e["button_label"], e.get("button_link")) + "</div>") if e.get("button_label") else ""
        items.append(f'''<li class="tl-item reveal"><span class="tl-year">{esc(e.get("year", ""))}</span><div class="tl-card">
  <span class="tl-img"><img src="{r[0] if r else ""}" alt="" loading="lazy"></span>
  <div class="tl-body"><h3>{esc(e.get("year", ""))} Folklore Projects</h3>{e.get("text", "")}{btn}</div></div></li>''')
    return f'''<div class="wrap article narrow"><div class="prose story">{re.sub("<p>", '<p class="dropcap">', d.get("intro") or "", count=1)}</div>{page_aside(page)}</div>
<section class="wrap block"><ol class="v-timeline">{"".join(items)}</ol></section>'''

def body_archive(page):
    d = PAGES[page]
    series = [(g.get("title") or "", photo_list(g.get("posters"))) for g in d.get("poster_groups") or []]
    tabs = '<button class="chip on" data-filter="all">All posters</button>' + "".join(
        f'<button class="chip" data-filter="s{i}">{esc(t)}</button>' for i, (t, _) in enumerate(series))
    figs = []
    for i, (t, items) in enumerate(series):
        for name, cap in items:
            r = img(name, 1000)
            if r:
                c = cap or t
                figs.append(f'<figure class="g-item poster" data-tag="s{i}"><a href="{r[1]}" class="lb" data-cap="{esc(c)}"><img src="{r[0]}" width="{r[2]}" height="{r[3]}" alt="{esc(c)}" loading="lazy"></a>'
                            f'<figcaption>{esc(cap) if cap else esc(t)}</figcaption></figure>')
    return f'''<section class="wrap block"><div class="section-head reveal"><h2 class="scribble">{esc(d.get("heading", ""))}</h2></div>
<div class="filterable"><div class="chips" role="toolbar" aria-label="Filter posters">{tabs}</div><div class="gallery posters">{"".join(figs)}</div></div></section>'''

def body_local(page):
    d = PAGES[page]
    intro = render(d.get("blocks"), page)
    logos = "".join(logo(P(l.get("image")), l.get("link"), l.get("name", "")) for l in d.get("logos") or [] if l.get("image"))
    return (f'<div class="wrap article narrow"><div class="prose story">{re.sub("<p>", "<p class=dropcap>", intro, count=1)}</div>{page_aside(page)}</div>'
            f'<section class="wrap block">{ORN}<div class="logo-wall">{logos}</div></section>')

def body_prarthana(page):
    d = PAGES[page]
    poem = d.get("poem") or {}
    stanzas = "".join("<p>" + "<br>".join(esc(x) for x in st.splitlines()) + "</p>" for st in poem.get("stanzas") or [] if st.strip())
    rec = d.get("recitation") or {}
    fig = figure(P(rec.get("image")), rec.get("caption"), rec.get("link") or None) if rec.get("image") else ""
    return f'''<div class="wrap article"><div class="prose story"><h3 class="subhead">{esc(d.get("intro_heading", ""))}</h3>{re.sub("<p>", '<p class="dropcap">', d.get("intro") or "", count=1)}
<div class="poem reveal"><h2>{esc(poem.get("title", ""))}</h2><p class="poem-by">{esc(poem.get("byline", ""))}</p>{stanzas}<p class="poem-credit">Credits: {esc(poem.get("credits", ""))}</p></div>
{fig}</div>{page_aside(page)}</div>'''

def body_fountain(page):
    d = PAGES[page]
    letter = d.get("letter") or {}
    pq = d.get("pull_quote") or {}
    body = re.sub(r"<p>", '<p class="dropcap">', render(d.get("blocks"), page), count=1)
    letter_body = "".join(f"<p>{esc(l)}</p>" for l in letter.get("paragraphs") or [] if l)
    quote = (f'<blockquote class="pull reveal"><p>{esc(pq["text"])}</p><cite>{esc(pq.get("by", ""))}</cite></blockquote>' if pq.get("text") else "")
    return f'''<div class="wrap article"><div class="prose story">{body}</div>{page_aside(page)}</div>
<section class="wrap wide-gallery">{ORN}<div class="section-head center"><h2 class="scribble">Photographs</h2></div>{gallery(photo_list(d.get("photos")), "grid", polaroid=True)}</section>
<section class="wrap block"><article class="letter reveal"><span class="stamp" aria-hidden="true"><img src="img/logo-badge.png" alt=""></span>
<p class="salute">{esc(letter.get("greeting", ""))}</p>{letter_body}<p class="sign">{esc(letter.get("closing", ""))}<br><span>{esc(letter.get("signed", ""))}</span></p></article>
{quote}</section>'''

def body_2026(page):
    doc = PAGES[page].get("documentary") or {}
    note = f'\n<p class="hand">{esc(doc["note"])}</p>' if doc.get("note") else ""
    vid = (f'\n<section class="wrap block"><div class="video-feature reveal">{video(F(doc["video"]), P(doc.get("poster")))}</div></section>'
           if doc.get("video") else "")
    return f'''<div class="wrap article narrow" id="macon-farm"><div class="prose story">
<h2 class="scribble">{esc(doc.get("title", ""))}</h2><p class="byline">{esc(doc.get("byline", ""))}</p><p class=dropcap>{esc(doc.get("text", ""))}</p>{note}</div>{page_aside(page)}</div>{vid}'''

def body_in_the_field(page):
    cards = "".join(
        f'<a class="duo-card tilt reveal" href="{esc(c.get("page", ""))}"><img src="{(img(P(c.get("image")), 900) or [""])[0]}" alt="" loading="lazy"><span><b>{esc(c.get("title", ""))}</b></span></a>'
        for c in PAGES[page].get("cards") or [])
    extra = f'<section class="band stitched"><div class="wrap"><div class="duo">{cards}</div></div></section>' if cards else ""
    return article(page, extra)

def body_gallery_page(page):
    out = []
    for b in PAGES[page].get("blocks") or []:
        if b.get("type") == "gallery":
            out.append(gallery(photo_list(b.get("photos")), "grid", polaroid=(page == "photo-gallery.html")))
        else:
            out.append(render([b], page))
    return f'<section class="wrap block">{"".join(out)}</section>'

SPECIAL = {
    "social.html": body_social, "contact-us.html": body_contact, "donations.html": body_donations,
    "events.html": body_events, "soil-to-soul-series.html": body_soil, "folk-projects.html": body_folk,
    "archive.html": body_archive, "local-support.html": body_local, "prarthana.html": body_prarthana,
    "episode-3-fountain.html": body_fountain, "2026.html": body_2026, "in-the-field.html": body_in_the_field,
}
PHOTO_PAGES = ("photo-gallery.html", "treasured-artists.html", "bill-ferris.html", "harrison.html")

def page_body(page):
    if page in SPECIAL:
        return SPECIAL[page](page)
    if page in PHOTO_PAGES:
        return body_gallery_page(page)
    return article(page)

# ================================================================ home page
def home():
    H = HOME
    slides_list = photo_list(H.get("slideshow"))
    slides = "".join(f'<img src="{img(n, 2000)[0]}" alt="{esc(c)}" data-cap="{esc(c)}" {"fetchpriority=high" if i == 0 else "loading=lazy"}>'
                     for i, (n, c) in enumerate(slides_list) if img(n, 2000))
    PHOTOS.extend(("index.html", n, c, img(n, 2000)[0]) for n, c in slides_list if img(n, 2000))
    scraps = [(n, c) for n, c in photo_list(H.get("scrapbook")) if img(n, 600)]
    PHOTOS.extend(("index.html", n, c, img(n, 600)[0]) for n, c in scraps)
    scrap_html = "".join(f'<figure class="scrap s{i}"><img src="{img(n, 600)[0]}" alt="{esc(c)}" loading="lazy"><figcaption>{esc(c)}</figcaption><span class="tape" aria-hidden="true"></span></figure>'
                         for i, (n, c) in enumerate(scraps))
    sc = H.get("showcase") or {}
    cards = "".join(
        f'<a class="card tilt reveal" href="{esc(c.get("page", ""))}"><span class="card-img"><img src="{(img(P(c.get("image")), 900) or [""])[0]}" alt="" loading="lazy"></span>'
        f'<span class="card-body"><span class="card-title">{esc(c.get("title", ""))}</span><span class="card-text">{esc(c.get("text", ""))}</span>'
        f'<span class="card-more">{esc(c.get("link_label", ""))} <span class="arr">→</span></span></span></a>'
        for c in sc.get("cards") or [])
    tlc = H.get("timeline") or {}
    def tl_cap(c, d):  # name the person in the photo when the text beside it is about something else
        return f'<span class="h-cap">{esc(c)}</span>' if c and " ".join(c.split()[:2]).rstrip(",") not in d else ""
    tl = "".join(
        f'<li class="h-item"><a href="{esc(e.get("page", ""))}"><span class="h-img"><img src="{(img(P(e.get("image")), 700) or [""])[0]}" alt="{esc(e.get("caption", ""))}" loading="lazy"></span>'
        f'{tl_cap(e.get("caption", ""), e.get("text", ""))}<span class="h-year">{esc(e.get("year", ""))}</span><span class="h-text">{esc(e.get("text", ""))}</span></a></li>'
        for e in tlc.get("entries") or [])
    sleeves = "".join(sleeve(e) for e in episodes())
    ls = H.get("listen") or {}
    tracks = "".join(player(F(t["file"]), t.get("title")) for t in ls.get("tracks") or [] if t.get("file"))
    po = H.get("posters") or {}
    prow = "".join(f'<img src="{img(P(p), 500)[0]}" alt="" loading="lazy">' for p in po.get("images") or [] if p and img(P(p), 500))
    mu = H.get("musicians") or {}
    roll = "".join(f"<li>{esc(m)}</li>" for m in mu.get("names") or [] if m)
    pa = H.get("partners") or {}
    plogos = "".join(logo(P(l.get("image")), l.get("link"), l.get("name", "")) for l in pa.get("logos") or [] if l.get("image"))
    btns = H.get("buttons") or []
    def hero_btn(i, b):
        u = href(b.get("link")) or "#"
        if i == 0:
            return f'<a class="btn btn-light" href="{esc(u)}">{esc(b.get("label", ""))}<span class="arr" aria-hidden="true">→</span></a>'
        ext = ' target="_blank" rel="noopener"' if u.startswith("http") else ""
        return f'<a class="btn btn-outline-light" href="{esc(u)}"{ext}>{esc(b.get("label", ""))}{" ↗" if ext else ""}</a>'
    hp = H.get("help") or {}
    hbtns = hp.get("buttons") or []
    help_btns = "".join(
        (f'<a class="btn btn-light" href="{esc(href(b.get("link")) or "#")}">{esc(b.get("label", ""))}<span class="arr" aria-hidden="true">→</span></a>' if i == 0
         else f'<a class="btn btn-outline-light" href="{esc(href(b.get("link")) or "#")}">{esc(b.get("label", ""))}</a>')
        for i, b in enumerate(hbtns))
    body = f'''
<section class="home-hero">
  <div class="hero-slides" aria-hidden="true">{slides}</div>
  <div class="wrap home-hero-inner">
    <div class="hero-badge-wrap"><img class="hero-badge" src="img/logo-badge-light.png" width="220" height="220" alt="SOOTS: Sustaining Roots Music, Raleigh NC, est. 2006"></div>
    <div class="hero-copy">
      <p class="hero-since">{esc(H.get("since", ""))}</p>
      <h1 class="hero-title">{esc(H.get("title", ""))}</h1>
      <p class="hero-lede">{esc(H.get("subtitle", ""))}</p>
      <div class="btn-row">{"".join(hero_btn(i, b) for i, b in enumerate(btns))}</div>
    </div>
  </div>
  <div class="hero-dots" aria-hidden="true"></div>
  <p class="hero-cap"></p>
  <div class="tear" aria-hidden="true"></div>
</section>
<section class="wrap intro">
  <div class="intro-grid">
    <div class="scrapbook reveal" aria-label="Photos from SOOTS events">{scrap_html}</div>
    <div class="prose">{re.sub("<p>", '<p class="dropcap">', para(H.get("intro")), count=1)}<p class="hand">{esc(H.get("motto", ""))}</p></div>
  </div>
</section>
<section class="band stitched">
  <div class="wrap">
    <div class="section-head reveal"><h2 class="scribble">{esc(sc.get("heading", ""))}</h2></div>
    <div class="cards">{cards}</div>
  </div>
</section>
<section class="timeline-sec">
  <div class="wrap section-head split reveal"><h2 class="scribble">{esc(tlc.get("heading", ""))}</h2>
    <div class="tl-ctrl"><button class="tl-btn" data-dir="-1" aria-label="Scroll timeline back">←</button><button class="tl-btn" data-dir="1" aria-label="Scroll timeline forward">→</button></div></div>
  <ol class="h-timeline" tabindex="0" aria-label="SOOTS timeline">{tl}</ol>
</section>
<section class="roll wrap reveal">
  <p class="roll-lead">{esc(mu.get("lead", ""), quote=False)}</p>
  <ul class="roll-names">{roll}</ul>
</section>
<section class="listen">
  <div class="wrap">
    <div class="section-head center reveal"><h2>{esc(ls.get("heading", ""))}</h2>{ORN}</div>
    <div class="sleeves">{sleeves}</div>
    <div class="listen-now reveal"><div class="players">{tracks}</div></div>
  </div>
</section>
<section class="poster-strip">
  <div class="wrap section-head split reveal"><h2 class="scribble">{esc(po.get("heading", ""))}</h2><a class="text-link" href="archive.html">{esc(po.get("link_label", ""))}</a></div>
  <a class="marquee" href="archive.html" aria-label="Poster archive"><div class="marquee-track">{prow}{prow}</div></a>
</section>
<section class="wrap partners">
  <div class="section-head center reveal"><h2>{esc(pa.get("heading", ""))}</h2>{ORN}</div>
  <div class="logo-wall">{plogos}</div>
  <p class="center"><a class="text-link" href="local-support.html">{esc(pa.get("link_label", ""))}</a></p>
</section>
<section class="cta">
  <div class="cta-disc vinyl spin" aria-hidden="true"><span class="label"><img src="img/logo-badge.png" alt=""></span></div>
  <div class="wrap cta-inner reveal">
    <h2>{esc(hp.get("heading", ""))}</h2>
    <p>{esc(hp.get("text", ""))}</p>
    <div class="btn-row">{help_btns}</div>
  </div>
</section>'''
    return head("Home", H.get("description") or SITE.get("default_description", ""), "index.html") + body + foot()

# ================================================================ photo names sheet
# pages whose photos show artists and guests (skips cakes, posters, and project photos)
NAMES_PAGES = ["index.html", "treasured-artists.html", "photo-gallery.html", "episode-1-this-little-light-of-ours.html",
               "episode-3-fountain.html", "fat-tuesday.html", "sit-downs.html", "events.html", "interviews.html"]
# captions worked out only from a photo's file name; someone who was there should confirm them
NAMES_TO_CHECK = {"johnd", "johnd2", "johnd2_1", "sam-john-dee-photo-7a", "4-05-08-soots-cake-bake-picture",
                  "eaux-claires-music-and-arts-festival-2018-the-guitarheels-with-iron-boy-a-collective-of-native-american-singers-and-dancers-from-the-great-lakes-regions-of-wisconsin-and-minnesota-62e5551d-ea2e-42c7-8d30-85b284ca6910-1-105-c"}

def names_sheet():
    """photo-names.html: photos of artists and guests with no caption yet, and captions that
    need checking. Open it in a browser (or print it), write in who is in each photo, then
    type the names into the photo captions in Pages CMS."""
    seen, groups, total, blank = set(), {}, 0, 0
    for page, name, cap, url in sorted(PHOTOS, key=lambda p: NAMES_PAGES.index(p[0]) if p[0] in NAMES_PAGES else 99):
        key = (page, stem_of(name))
        if key in seen or page not in NAMES_PAGES:
            continue
        seen.add(key)
        total += 1
        blank += not cap
        if cap and stem_of(name) not in NAMES_TO_CHECK:
            continue
        groups.setdefault(page, []).append((name, cap, url, stem_of(name) in NAMES_TO_CHECK))
    sections = []
    for page, items in groups.items():
        title = "Home page" if page == "index.html" else title_of(page)
        cells = "".join(
            f'<div class="item"><img src="site/{u}" alt="" loading="lazy">'
            + (f'<p>Is this right? <b>{esc(c)}</b></p>' if chk else "<p>Who is in this photo? (blank if no one)</p>")
            + f'<p class="line"></p><p class="file">{esc(os.path.basename(n))}</p></div>'
            for n, c, u, chk in items)
        sections.append(f'<h2>{esc(title)} <a href="site/{page}">({page})</a></h2><div class="grid">{cells}</div>')
    to_check = sum(1 for items in groups.values() for *_, chk in items if chk)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOOTS photos that need names</title>
<style>
body{{font:16px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:24px;color:#222;background:#fff}}
h1{{font-size:24px;margin:0 0 6px}} h2{{font-size:18px;margin:28px 0 10px;border-bottom:1px solid #ddd;padding-bottom:4px}}
h2 a{{font-weight:400;font-size:14px;color:#777}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px}}
.item{{break-inside:avoid;border:1px solid #ddd;padding:8px}} .item img{{width:100%;height:160px;object-fit:cover;display:block}}
.item p{{margin:6px 0 0;font-size:14px}} .line{{border-bottom:1px solid #999;height:34px}} .file{{color:#888;font-size:11px!important;word-break:break-all}}
</style></head><body>
<h1>SOOTS photos that need names</h1>
<p>On the pages with artists and guests, {total} photos are shown: {total - blank} have a caption, {blank} have none yet, and {to_check} captions need checking.
Write who is in each photo below, then type the names into that photo's caption in Pages CMS (the small file name under each photo helps you find it).</p>
{"".join(sections)}
</body></html>"""
    open(os.path.join(ROOT, "photo-names.html"), "w").write(doc)
    return total, blank, to_check

# ================================================================ build
def build():
    if os.path.exists(OUT):
        for sub in ("css", "js"):
            shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
        for f in os.listdir(OUT):
            if f.endswith(".html"):
                os.remove(os.path.join(OUT, f))
    for d in (OUT, IMG_DIR, FULL_DIR, os.path.join(OUT, "media")):
        os.makedirs(d, exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "assets", "css"), os.path.join(OUT, "css"))
    shutil.copytree(os.path.join(ROOT, "assets", "js"), os.path.join(OUT, "js"))
    brand_assets()
    CUR["page"] = "index.html"
    open(os.path.join(OUT, "index.html"), "w").write(home())
    for page in PAGES:
        CUR["page"] = page
        doc = head(title_of(page), description(page), page) + hero(page) + page_body(page) + pager(page) + foot()
        open(os.path.join(OUT, page), "w").write(doc)
    open(os.path.join(OUT, "404.html"), "w").write(
        head("Page not found", "Page not found", "404.html") +
        '<section class="page-hero"><div class="wrap hero-inner"><p class="kicker">404</p><h1>Page not found</h1></div><div class="tear" aria-hidden="true"></div></section>'
        '<section class="wrap block center"><div class="vinyl big spin" aria-hidden="true"><span class="label"><img src="img/logo-badge.png" alt=""></span></div>'
        '<div class="btn-row center"><a class="btn" href="index.html">Back to the home page</a></div></section>' + foot())
    # the old site's Macon Farm address now forwards to the 2026 page
    open(os.path.join(OUT, "macon-farm-documentary.html"), "w").write(
        '<!doctype html><meta charset="utf-8"><title>The Macon Farm · SOOTS Blues</title>'
        f'<link rel="canonical" href="{SITE_URL}2026.html">'
        '<meta http-equiv="refresh" content="0; url=2026.html#macon-farm"><a href="2026.html#macon-farm">The Macon Farm</a>')
    open(os.path.join(OUT, "CNAME"), "w").write(re.sub(r"^https?://|/.*$", "", SITE_URL) + "\n")
    print("built", len([f for f in os.listdir(OUT) if f.endswith(".html")]), "pages",
          f"with {len(WARNINGS)} warning(s) (see above)" if WARNINGS else "")
    if "--names-sheet" in sys.argv:
        total, blank, check = names_sheet()
        print(f"photo-names.html: {total} photos of artists and guests, {total - blank} captioned, {blank} without a caption, {check} to check")

def brand_assets():
    src_path = find_src(P(SITE.get("logo")))
    if not src_path:
        sys.exit("\nBUILD STOPPED: the logo set in Site settings (content/site.json) is missing from content/photos.")
    src = Image.open(src_path).convert("RGBA")
    for name, color, size in (("logo-badge.png", (31, 27, 22), 160), ("logo-badge-light.png", (243, 236, 223), 440)):
        g = ImageOps.invert(src.convert("L"))
        alpha = Image.composite(g, Image.new("L", src.size, 0), src.split()[3]).point(lambda v: min(255, int(v * 1.6)))
        out = Image.new("RGBA", src.size, color + (0,))
        out.putalpha(alpha)
        out.resize((size, size), Image.LANCZOS).save(os.path.join(IMG_DIR, name), optimize=True)
    Image.open(os.path.join(IMG_DIR, "logo-badge.png")).resize((64, 64), Image.LANCZOS).save(os.path.join(IMG_DIR, "favicon.png"))
    share = find_src(P(SITE.get("share_image"))) or src_path
    og = ImageOps.fit(Image.open(share).convert("RGB"), (1200, 630))
    og.save(os.path.join(IMG_DIR, "og.jpg"), quality=82)

if __name__ == "__main__":
    build()
