#!/usr/bin/env python3
"""Publish the architecture documents from a git revision to Confluence Cloud.

GitHub is the source of truth, so the text is read from a git revision (origin/main by
default), never from the working tree. Publishing is safe to repeat: pages are found by
title, and a page whose content has not changed is skipped.

Commands:
  dry-run   Convert and validate every document, and write the output to --out. No network.
  check     Confirm the credentials, the space and the two parent pages.
  publish   Create or update the pages, and attach the Draw.io diagram.

Mermaid diagrams use the Mermaid app by Narva Software, which must be installed on the site.
The page shows the Draw.io diagram only if its PNG export is committed next to the .drawio file.

Credentials come from CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN, or from the file
~/.config/notification-service/confluence.env, which must be readable only by its owner.
The token is sent only in the Authorization header and is never printed.

Standard library only.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import pathlib
import posixpath
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET

DEFAULT_SITE = "https://calegariltda.atlassian.net"
SPACE_KEY = "NTS"
ARCHITECTURE_PARENT = "917506"
ADR_PARENT = "950273"
BASE = "docs/architecture/notification-service"
DIAGRAM = f"{BASE}/diagrams/notification-platform-hld.drawio"
HLD = f"{BASE}/high-level-design.md"
GITHUB = "https://github.com/gcmercante/notification-service/blob"
CREDENTIALS_FILE = pathlib.Path.home() / ".config/notification-service/confluence.env"
DIAGRAM_PNG = DIAGRAM.removesuffix(".drawio") + ".png"
REV_PLACEHOLDER = "@@REV@@"

# Forge macro of the Mermaid app, copied from a diagram inserted with the Confluence editor.
MERMAID_EXTENSION = "336440d6-2d95-4275-833f-6351e86634e3/e5743d37-53d6-4daa-a3a1-acca68790e69/static/mermaid-diagram"
# Languages the Confluence code macro highlights. Anything else is sent without one.
CODE_LANGUAGES = {"bash", "java", "javascript", "json", "powershell", "python", "sql", "typescript", "xml", "yaml"}


class PublishError(Exception):
    pass


# Markdown to Confluence storage format. Handles only what these documents use.


def inline(text, src_dir):
    # Hold code spans aside, so links and bold that wrap them still convert.
    codes = []

    def hold(match):
        codes.append(f"<code>{html.escape(match.group(1), quote=False)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    result = re.sub(r"`([^`]+)`", hold, text)
    result = html.escape(result, quote=False)
    result = re.sub(r"&lt;(/?)(sub|sup)&gt;", r"<\1\2>", result)

    def link(match):
        label, url = match.group(1), match.group(2)
        if url.startswith("#"):
            return label
        if not url.startswith("http"):
            path, _, fragment = url.partition("#")
            full = posixpath.normpath(posixpath.join(src_dir, path))
            url = f"{GITHUB}/{REV_PLACEHOLDER}/{full}" + (f"#{fragment}" if fragment else "")
        # The text is already escaped, apart from quotes.
        return f'<a href="{url.replace(chr(34), "&quot;")}">{label}</a>'

    result = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, result)
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"~~(.+?)~~", r"<s>\1</s>", result)
    result = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", result)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], result)


def split_cells(line):
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace("\\|", "|") for cell in cells]


def parse_list(lines, i, src_dir):
    item = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
    first = item.match(lines[i])
    base = len(first.group(1))
    tag = "ol" if first.group(2)[0].isdigit() else "ul"
    buf = [f"<{tag}>"]
    while i < len(lines):
        match = item.match(lines[i])
        if not match or len(match.group(1)) < base:
            if match is None and lines[i].strip() and lines[i].startswith(" " * (base + 2)):
                buf[-1] = buf[-1][:-5] + " " + inline(lines[i].strip(), src_dir) + "</li>"
                i += 1
                continue
            next_is_item = i + 1 < len(lines) and item.match(lines[i + 1])
            if match is None and not lines[i].strip() and next_is_item and len(next_is_item.group(1)) >= base:
                i += 1
                continue
            break
        if len(match.group(1)) > base:
            sub, i = parse_list(lines, i, src_dir)
            buf[-1] = buf[-1][:-5] + sub + "</li>"
            continue
        buf.append(f"<li>{inline(match.group(3), src_dir)}</li>")
        i += 1
    buf.append(f"</{tag}>")
    return "".join(buf), i


def cdata(text):
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def code_macro(code, lang):
    language = f'<ac:parameter ac:name="language">{lang}</ac:parameter>' if lang in CODE_LANGUAGES else ""
    return f'<ac:structured-macro ac:name="code">{language}<ac:plain-text-body>{cdata(code)}</ac:plain-text-body></ac:structured-macro>'


def mermaid_macro(code):
    # Forge macros are stored as ADF, with the same node repeated as the fallback. The id is
    # derived from the code so that unchanged diagrams keep the page's digest stable.
    local_id = str(uuid.uuid5(uuid.NAMESPACE_URL, code))
    node = (
        '<ac:adf-node type="extension">'
        f'<ac:adf-attribute key="extension-key">{MERMAID_EXTENSION}</ac:adf-attribute>'
        '<ac:adf-attribute key="extension-type">com.atlassian.ecosystem</ac:adf-attribute>'
        '<ac:adf-attribute key="parameters">'
        f'<ac:adf-parameter key="local-id">{local_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-id">ari:cloud:ecosystem::extension/{MERMAID_EXTENSION}</ac:adf-parameter>'
        '<ac:adf-parameter key="extension-title">Mermaid Diagram</ac:adf-parameter>'
        '<ac:adf-parameter key="layout">extension</ac:adf-parameter>'
        '<ac:adf-parameter key="forge-environment">PRODUCTION</ac:adf-parameter>'
        f'<ac:adf-parameter key="guest-params"><ac:adf-parameter key="code">{html.escape(code)}</ac:adf-parameter></ac:adf-parameter>'
        "</ac:adf-attribute>"
        '<ac:adf-attribute key="text">Mermaid Diagram</ac:adf-attribute>'
        '<ac:adf-attribute key="layout">default</ac:adf-attribute>'
        f'<ac:adf-attribute key="local-id">{local_id}</ac:adf-attribute>'
        "</ac:adf-node>"
    )
    return f"<ac:adf-extension>{node}<ac:adf-fallback>{node}</ac:adf-fallback></ac:adf-extension>"


def convert(markdown, src_dir):
    lines = markdown.split("\n")
    out, i = [], 0
    block_start = re.compile(r"^(#{1,6}\s|```|\||>|\s*([-*]|\d+\.)\s|-{3,}\s*$)")
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            lang = line[3:].strip()
            end = i + 1
            while not lines[end].startswith("```"):
                end += 1
            code = "\n".join(lines[i + 1 : end])
            out.append(mermaid_macro(code) if lang == "mermaid" else code_macro(code, lang))
            i = end + 1
        elif re.match(r"^#{1,6}\s", line):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip(), src_dir)}</h{level}>")
            i += 1
        elif re.match(r"^-{3,}\s*$", line):
            out.append("<hr />")
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            table = "<table><tbody><tr>" + "".join(f"<th>{inline(c, src_dir)}</th>" for c in split_cells(rows[0])) + "</tr>"
            for row in rows[2:]:
                table += "<tr>" + "".join(f"<td>{inline(c, src_dir)}</td>" for c in split_cells(row)) + "</tr>"
            out.append(table + "</tbody></table>")
        elif line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").lstrip())
                i += 1
            out.append("<blockquote>" + convert("\n".join(buf), src_dir) + "</blockquote>")
        elif re.match(r"^\s*([-*]|\d+\.)\s+", line):
            rendered, i = parse_list(lines, i, src_dir)
            out.append(rendered)
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not block_start.match(lines[i]):
                buf.append(lines[i].strip())
                i += 1
            if not buf:  # A line block_start accepts but no branch above consumed.
                raise PublishError(f"Cannot convert line {i + 1} in {src_dir}: {line[:80]}")
            out.append("<p>" + inline(" ".join(buf), src_dir) + "</p>")
    return "".join(out)


def status_macro(text, colour):
    return (
        '<ac:structured-macro ac:name="status">'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f'<ac:parameter ac:name="title">{text}</ac:parameter>'
        "</ac:structured-macro>"
    )


def banner(path):
    return (
        '<ac:structured-macro ac:name="info"><ac:rich-text-body><p><strong>This page is a copy.</strong> '
        f'The source of truth is <a href="{GITHUB}/{REV_PLACEHOLDER}/{path}">{posixpath.basename(path)} on GitHub</a>. '
        "Change the repository first, then publish again.</p></ac:rich-text-body></ac:structured-macro>"
    )


def diagram_section(has_png):
    name = posixpath.basename(DIAGRAM)
    link = f'<ac:link><ri:attachment ri:filename="{name}" /><ac:plain-text-link-body>{cdata(name)}</ac:plain-text-link-body></ac:link>'
    image = f'<ac:image><ri:attachment ri:filename="{posixpath.basename(DIAGRAM_PNG)}" /></ac:image>' if has_png else ""
    return f"<h2>Architecture diagram</h2>{image}<p>The editable diagram is attached to this page: {link}. Open it with draw.io.</p>"


def assert_well_formed(storage, path):
    root = f'<root xmlns:ac="urn:ac" xmlns:ri="urn:ri">{storage}</root>'
    try:
        ET.fromstring(root)
    except ET.ParseError as error:
        raise PublishError(f"{path} converted to invalid storage format: {error}") from error


def build_page(markdown, path, has_png=False):
    match = re.match(r"^# (.+)\n", markdown)
    if not match:
        raise PublishError(f"{path} does not start with a level 1 heading")
    body = convert(markdown.split("\n", 1)[1], posixpath.dirname(path))
    body = re.sub(r"(<td>Status</td><td>)Accepted(</td>)", rf'\g<1>{status_macro("Accepted", "Green")}\2', body)
    storage = banner(path) + (diagram_section(has_png) if path == HLD else "") + body
    assert_well_formed(storage, path)
    return match.group(1), storage


# Git


def git(*args, binary=False):
    result = subprocess.run(["git", *args], capture_output=True, check=False)
    if result.returncode != 0:
        raise PublishError(f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout if binary else result.stdout.decode()


def document_paths(rev):
    names = git("ls-tree", "-r", "--name-only", rev, "--", BASE).splitlines()
    adrs = sorted(n for n in names if re.fullmatch(rf"{BASE}/decisions/\d{{4}}-[^/]+\.md", n))
    pages = [(path, ADR_PARENT) for path in adrs]
    for path in (f"{BASE}/architecture-context.md", HLD):
        if path not in names:
            raise PublishError(f"{path} is not in revision {rev[:7]}")
        pages.append((path, ARCHITECTURE_PARENT))
    return pages


def has_png(rev):
    return bool(git("ls-tree", "--name-only", rev, "--", DIAGRAM_PNG).strip())


def load_pages(rev):
    pages = []
    png = has_png(rev)
    for path, parent in document_paths(rev):
        title, storage = build_page(git("show", f"{rev}:{path}", binary=True).decode("utf-8"), path, png)
        digest = hashlib.sha256(storage.encode()).hexdigest()[:16]  # Before the revision goes in.
        pages.append({"path": path, "parent": parent, "title": title, "digest": digest, "storage": storage.replace(REV_PLACEHOLDER, rev)})
    return pages


# Confluence client


def load_credentials():
    email, token = os.environ.get("CONFLUENCE_EMAIL"), os.environ.get("CONFLUENCE_API_TOKEN")
    if email and token:
        return email, token
    if CREDENTIALS_FILE.exists():
        if stat.S_IMODE(CREDENTIALS_FILE.stat().st_mode) & 0o077:
            raise PublishError(f"{CREDENTIALS_FILE} must be readable only by you. Run: chmod 600 {CREDENTIALS_FILE}")
        values = dict(ln.split("=", 1) for ln in CREDENTIALS_FILE.read_text().splitlines() if "=" in ln and not ln.startswith("#"))
        email, token = values.get("CONFLUENCE_EMAIL", "").strip(), values.get("CONFLUENCE_API_TOKEN", "").strip()
        if email and token:
            return email, token
    raise PublishError(f"No credentials. Set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN, or create {CREDENTIALS_FILE}")


class Confluence:
    def __init__(self, site, email, token):
        parsed = urllib.parse.urlparse(site)
        if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise PublishError("Refusing to send the API token over a connection that is not HTTPS")
        self.site = site.rstrip("/")
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

    def raw(self, method, path, body=None, headers=None, retries=4):
        request = urllib.request.Request(self.site + path, data=body, method=method)
        request.add_header("Authorization", self.auth)
        request.add_header("Accept", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            if error.code in (429, 503) and retries > 0:
                time.sleep(min(int(error.headers.get("Retry-After") or 5), 60))
                return self.raw(method, path, body, headers, retries - 1)
            return error.code, error.read()

    def json(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        code, data = self.raw(method, path, body, {"Content-Type": "application/json"} if body else None)
        if code >= 300:
            raise PublishError(f"{method} {path} returned {code}: {data.decode(errors='replace')[:800]}")
        return json.loads(data) if data else {}

    def space_id(self):
        results = self.json("GET", f"/wiki/api/v2/spaces?keys={SPACE_KEY}")["results"]
        if not results:
            raise PublishError(f"Space {SPACE_KEY} was not found, or this token cannot see it")
        return results[0]["id"]

    def find_page(self, space_id, title):
        query = urllib.parse.urlencode({"space-id": space_id, "title": title, "status": "current"})
        results = self.json("GET", f"/wiki/api/v2/pages?{query}")["results"]
        return results[0] if results else None

    def create_page(self, space_id, page):
        payload = {
            "spaceId": space_id,
            "status": "current",
            "title": page["title"],
            "parentId": page["parent"],
            "body": {"representation": "storage", "value": page["storage"]},
        }
        return self.json("POST", "/wiki/api/v2/pages", payload)

    def update_page(self, existing, page, message):
        payload = {
            "id": existing["id"],
            "status": "current",
            "title": page["title"],
            "parentId": page["parent"],
            "body": {"representation": "storage", "value": page["storage"]},
            "version": {"number": existing["version"]["number"] + 1, "message": message},
        }
        return self.json("PUT", f"/wiki/api/v2/pages/{existing['id']}", payload)

    def attach(self, page_id, filename, content, content_type):
        """Upload the file unless the page already holds this content. Returns whether it uploaded."""
        comment = f"sync {hashlib.sha256(content).hexdigest()[:16]}"
        query = urllib.parse.urlencode({"filename": filename})
        current = self.json("GET", f"/wiki/rest/api/content/{page_id}/child/attachment?{query}")["results"]
        if current and current[0].get("metadata", {}).get("comment") == comment:
            return False
        boundary = uuid.uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="comment"\r\n\r\n{comment}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "X-Atlassian-Token": "no-check"}
        code, data = self.raw("PUT", f"/wiki/rest/api/content/{page_id}/child/attachment", body, headers)
        if code >= 300:
            raise PublishError(f"Attaching {filename} returned {code}: {data.decode(errors='replace')[:800]}")
        return True


# Commands


def resolve_rev(args):
    rev = args.rev or "origin/main"
    if not args.rev:
        git("fetch", "--quiet", "origin", "main")
    return git("rev-parse", "--verify", f"{rev}^{{commit}}").strip()


def cmd_dry_run(args):
    rev = resolve_rev(args)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pages = load_pages(rev)
    for page in pages:
        (out / (posixpath.basename(page["path"])[:-3] + ".xml")).write_text(page["storage"], encoding="utf-8")
        print(f"{len(page['storage']):>8}  {page['title'][:90]}")
    print(f"Converted {len(pages)} documents from {rev[:7]} into {out}. All are well formed.")


def cmd_check(args):
    client = Confluence(args.site, *load_credentials())
    print(f"Space {SPACE_KEY}: id {client.space_id()}")
    for page_id in (ARCHITECTURE_PARENT, ADR_PARENT):
        print(f"Parent {page_id}: {client.json('GET', f'/wiki/api/v2/pages/{page_id}')['title']}")
    print("Credentials and targets are fine.")


def cmd_publish(args):
    rev = resolve_rev(args)
    pages = load_pages(rev)
    client = Confluence(args.site, *load_credentials())
    space_id = client.space_id()
    site_url = client.site
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    hld_id = None
    for page in pages:
        existing = client.find_page(space_id, page["title"])
        message = f"sync {page['digest']} from {rev[:7]}"
        if existing is None:
            saved, action = client.create_page(space_id, page), "created"
        elif page["digest"] in ((existing.get("version") or {}).get("message") or "") and existing.get("parentId") == page["parent"]:
            saved, action = existing, "unchanged"
        else:
            saved, action = client.update_page(existing, page, message), "updated"
        counts[action] += 1
        if page["path"] == HLD:
            hld_id = saved["id"]
        print(f"{action:>9}  {saved['id']}  {page['title'][:80]}", flush=True)
    files = [(DIAGRAM, "application/vnd.jgraph.mxfile")] + ([(DIAGRAM_PNG, "image/png")] if has_png(rev) else [])
    for path, content_type in files:
        name = posixpath.basename(path)
        uploaded = client.attach(hld_id, name, git("show", f"{rev}:{path}", binary=True), content_type)
        print(f"{'Attached' if uploaded else 'Unchanged:'} {name} on page {hld_id}")
    print(f"Done from {rev[:7]}: {counts}. See {site_url}/wiki/spaces/{SPACE_KEY}/pages/{ARCHITECTURE_PARENT}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["dry-run", "check", "publish"])
    parser.add_argument("--rev", help="git revision to publish (default: origin/main, fetched first)")
    parser.add_argument("--site", default=os.environ.get("CONFLUENCE_SITE", DEFAULT_SITE))
    parser.add_argument("--out", default="confluence-dry-run", help="output directory for dry-run")
    args = parser.parse_args()
    commands = {"dry-run": cmd_dry_run, "check": cmd_check, "publish": cmd_publish}
    try:
        commands[args.command](args)
    except PublishError as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
