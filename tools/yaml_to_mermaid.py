"""Generate a Mermaid flowchart from a ypack YAML configuration.

Usage:
    python -m tools.yaml_to_mermaid input.yaml -o output.mmd

The tool produces a simple `flowchart LR` that shows the `app`, `install`, `variables`,
`files` and `packages` (including parent->child package relationships). The output is
plain Mermaid source which can be opened with mermaid.live or VS Code Mermaid preview
plugins.
"""

from __future__ import annotations

import argparse
import io
import sys
import textwrap
import yaml
from typing import Any, Dict, Iterable


def sanitize_id(name: str) -> str:
    # Keep only letters, digits and underscores for node ids
    return "n_" + "".join(c if c.isalnum() else "_" for c in name)


def escape_label(s: str, max_len: int = 80, br: bool = True) -> str:
    if s is None:
        return ""
    s = str(s)
    # Normalize different line endings to \n
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    # Use HTML line break when requested so Mermaid renders multi-line labels
    if br:
        s = s.replace("\n", "<br>")
    else:
        s = s.replace("\n", " ")
    return s.replace("\"", "\\\"")


def render_app_node(app: Dict[str, Any]) -> str:
    name = app.get("name", "<unnamed>")
    version = app.get("version")
    label = f"App: {name}"
    if version:
        label += f"<br>v{version}"
    node_id = sanitize_id("app")
    return f'{node_id}["{escape_label(label, 120)}"]\n', node_id


def render_install_node(install: Dict[str, Any]) -> str:
    label_lines = []
    if not install:
        label_lines.append("install: <none>")
    else:
        d = install.get("install_dir")
        if d:
            label_lines.append(f"dir: {d}")
        ds = install.get("desktop_shortcut")
        sm = install.get("start_menu_shortcut")
        if ds:
            t = ds.get("target") if isinstance(ds, dict) else ds
            label_lines.append(f"desktop -> {t}")
        if sm:
            t = sm.get("target") if isinstance(sm, dict) else sm
            label_lines.append(f"start menu -> {t}")
        # existing install
        ei = install.get("existing_install")
        if isinstance(ei, dict):
            mode = ei.get("mode")
            if mode:
                label_lines.append(f"existing: {mode}")
        elif isinstance(ei, str):
            label_lines.append(f"existing: {ei}")
    label = "<br>".join(label_lines)
    node_id = sanitize_id("install")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_registry_node(regs: Iterable[Dict[str, Any]]) -> tuple[str, str]:
    regs = list(regs or [])
    if not regs:
        label = "registry: <none>"
    else:
        lines = []
        for r in regs[:6]:
            hive = r.get("hive", "")
            key = r.get("key", "")
            name = r.get("name", "")
            lines.append(f"{hive}<br>{key}<br>{name}")
        if len(regs) > 6:
            lines.append(f"... (+{len(regs)-6} more)")
        label = "<br>".join(lines)
    node_id = sanitize_id("registry_entries")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_env_vars_node(env_vars: Iterable[Dict[str, Any]]) -> tuple[str, str]:
    env_vars = list(env_vars or [])
    if not env_vars:
        label = "env_vars: <none>"
    else:
        lines = []
        for e in env_vars[:6]:
            name = e.get("name")
            val = e.get("value")
            scope = e.get("scope")
            rm = e.get("remove_on_uninstall")
            lines.append(f"{name}={val} ({scope}){' rm' if rm else ''}")
        if len(env_vars) > 6:
            lines.append(f"... (+{len(env_vars)-6} more)")
        label = "<br>".join(lines)
    node_id = sanitize_id("env_vars")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_file_assocs_node(assocs: Iterable[Dict[str, Any]]) -> tuple[str, str]:
    assocs = list(assocs or [])
    if not assocs:
        label = "file_associations: <none>"
    else:
        lines = []
        for a in assocs[:6]:
            ext = a.get("extension")
            app = a.get("application")
            verbs = a.get("verbs")
            vdesc = ",".join(sorted(verbs.keys())) if isinstance(verbs, dict) else ""
            lines.append(f"{ext} -> {vdesc} {app or ''}")
        if len(assocs) > 6:
            lines.append(f"... (+{len(assocs)-6} more)")
        label = "<br>".join(lines)
    node_id = sanitize_id("file_assocs")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_variables_node(variables: Dict[str, Any]) -> str:
    if not variables:
        label = "variables: <none>"
    else:
        # show up to first 6 variables
        items = list(variables.items())[:6]
        lines = [f"{k}={escape_label(v, 40)}" for k, v in items]
        if len(variables) > 6:
            lines.append(f"... (+{len(variables)-6} more)")
        label = "<br>".join(lines)
    node_id = sanitize_id("variables")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_files_node(files: Iterable[Any]) -> str:
    files = list(files or [])
    if not files:
        label = "files: <none>"
    else:
        # show up to 6 file entries with destination/checksum/decompress
        lines = []
        for f in files[:6]:
            if isinstance(f, str):
                lines.append(f)
            elif isinstance(f, dict):
                src = f.get("source") or f.get("sources")
                dest = f.get("destination")
                ch = f.get("checksum_type")
                dec = f.get("decompress")
                parts = [str(src)]
                if dest:
                    parts.append(f"-> {dest}")
                if ch:
                    parts.append(f"[{ch}]")
                if dec:
                    parts.append("(decompress)")
                lines.append(" ".join(parts))
            else:
                lines.append(str(f))
        if len(files) > 6:
            lines.append(f"... (+{len(files)-6} more)")
        label = "<br>".join(lines)
    node_id = sanitize_id("files")
    return f'{node_id}["{escape_label(label, 200)}"]\n', node_id


def render_packages(packages: Dict[str, Any], files: Iterable[Any] | None = None) -> tuple[str, list[str], Dict[str, dict]]:
    """Render packages as subgraphs. Also map files into packages when possible and
    return package info dict used for interactive HTML sidebar.

    Returns:
        body (str), top_level_nodes (list of node ids), package_info (mapping name -> details)
    """
    if not packages:
        node = 'p_none["packages: <none>"]\n'
        return node, [], {}

    # Build a simple map of package -> source patterns
    pkg_sources: Dict[str, list[str]] = {}
    for name, entry in packages.items():
        srcs = []
        if isinstance(entry, dict):
            sources = entry.get("sources") or entry.get("source")
            if isinstance(sources, str):
                srcs.append(sources)
            elif isinstance(sources, list):
                for s in sources:
                    srcs.append(str(s))
        pkg_sources[name] = srcs

    # map files to packages (simple heuristic: startswith match)
    files = list(files or [])
    file_map: Dict[str, list[dict]] = {name: [] for name in packages.keys()}
    unassigned_files: list[dict] = []
    for f in files:
        src = None
        if isinstance(f, str):
            src = f
        elif isinstance(f, dict):
            src = f.get("source") or f.get("sources")
            if isinstance(src, list):
                src = src[0]
        else:
            src = str(f)
        if not src:
            unassigned_files.append({"src": src})
            continue
        matched = False
        for pkg_name, patterns in pkg_sources.items():
            for p in patterns:
                if p.endswith("/*"):
                    base = p[:-2]
                    if str(src).startswith(base):
                        file_map[pkg_name].append({"src": src, "raw": f})
                        matched = True
                        break
                else:
                    if str(src) == p or str(src).startswith(p):
                        file_map[pkg_name].append({"src": src, "raw": f})
                        matched = True
                        break
            if matched:
                break
        if not matched:
            unassigned_files.append({"src": src, "raw": f})

    body_lines = []
    top_level_nodes: list[str] = []
    package_info: Dict[str, dict] = {}

    def walk(pkg_map: Dict[str, Any], parent_id: str | None = None) -> None:
        for name, entry in pkg_map.items():
            pkg_node_id = sanitize_id(f"pkg_{name}")
            if parent_id is None:
                top_level_nodes.append(pkg_node_id)
            # record info
            info: dict = {
                "name": name,
                "optional": bool(entry.get("optional") if isinstance(entry, dict) else False),
                "default": bool(entry.get("default") if isinstance(entry, dict) else False),
                "description": entry.get("description") if isinstance(entry, dict) else None,
                "sources": [],
                "post_install": entry.get("post_install") if isinstance(entry, dict) else None,
                "files": file_map.get(name, []),
            }
            sources = entry.get("sources") or entry.get("source") if isinstance(entry, dict) else None
            if isinstance(sources, str):
                info["sources"] = [sources]
            elif isinstance(sources, list):
                info["sources"] = [str(s) for s in sources]
            package_info[name] = info

            # build label
            parts = [name]
            if isinstance(entry, dict):
                if entry.get("optional"):
                    parts.append("(optional)")
                if entry.get("default"):
                    parts.append("(default)")
                desc = entry.get("description")
                if desc:
                    parts.append(escape_label(desc, 60))
                # sources summary
                src_list = info["sources"] if info.get("sources") else []
                if src_list:
                    parts.append("sources: " + ", ".join(escape_label(s, 40) for s in src_list))
                if entry.get("post_install"):
                    parts.append("post_install")
            else:
                parts.append(escape_label(str(entry), 60))
            label = "<br>".join(parts)

            children = entry.get("children") if isinstance(entry, dict) else None
            # subgraph holding pkg and its files
            sg_id = sanitize_id(f"sg_{name}")
            body_lines.append(f'subgraph {sg_id}["{escape_label(name)}"]')
            # parent node inside subgraph
            body_lines.append(f'{pkg_node_id}["{escape_label(label, 200)}"]')
            # add package class markers
            if isinstance(entry, dict):
                if entry.get("optional"):
                    body_lines.append(f"class {pkg_node_id} pkg_optional")
                if entry.get("default"):
                    body_lines.append(f"class {pkg_node_id} pkg_default")
            # add click handler placeholder
            body_lines.append(f"click {pkg_node_id} showPkg(\"{name}\")")
            # render files assigned to this package
            for fi in file_map.get(name, []):
                fid = sanitize_id(f"file_{name}_{len(fi['src'])}_{abs(hash(fi['src']))%10000}")
                f_label = escape_label(fi['src'], 100)
                body_lines.append(f'{fid}["{f_label}"]')
                body_lines.append(f"{pkg_node_id} --> {fid}")
            # recurse for children
            if children:
                walk(children, parent_id=pkg_node_id)
            body_lines.append("end")

            if parent_id:
                body_lines.append(f"{parent_id} --> {pkg_node_id}")

    walk(packages, parent_id=None)

    # Put unassigned files separately
    if unassigned_files:
        body_lines.append('subgraph n_unassigned_files["Unassigned files"]')
        for u in unassigned_files:
            fid = sanitize_id(f"file_un_{len(u.get('src') or '')}_{abs(hash(u.get('src') or ''))%10000}")
            body_lines.append(f'{fid}["{escape_label(u.get("src"), 100)}"]')
        body_lines.append("end")

    return "\n".join(body_lines) + "\n", top_level_nodes, package_info

def generate_mermaid(data: Dict[str, Any]) -> str:
    parts = []
    parts.append("flowchart LR")
    parts.append("%% Styles")
    parts.append("classDef app fill:#ffd6a5,stroke:#333,stroke-width:1.5px;")
    parts.append("classDef install fill:#cfe8ff,stroke:#333,stroke-width:1px;")
    parts.append("classDef pkg_optional fill:#fff3cd,stroke:#333,stroke-width:1px;")
    parts.append("classDef pkg_default fill:#e6ffed,stroke:#333,stroke-width:1px;")
    parts.append("classDef meta fill:#f0f0f0,stroke:#999,stroke-width:1px;")
    # App
    app_node, app_id = render_app_node(data.get("app", {}))
    parts.append(app_node)
    parts.append(f"class {app_id} app")

    # Install
    install_node, install_id = render_install_node(data.get("install", {}))
    parts.append(install_node)
    parts.append(f"class {install_id} install")
    parts.append(f"{app_id} --> {install_id}")

    # Variables
    vars_node, vars_id = render_variables_node(data.get("variables", {}))
    parts.append(vars_node)
    parts.append(f"{app_id} --> {vars_id}")

    # Files
    files_node, files_id = render_files_node(data.get("files", []))
    parts.append(files_node)
    parts.append(f"{app_id} --> {files_id}")

    # Packages (map files to packages when possible)
    pkgs, pkg_nodes, pkg_info = render_packages(data.get("packages", {}), data.get("files", []))
    parts.append(pkgs)
    # connect app -> each top-level package node
    for n in pkg_nodes:
        parts.append(f"{app_id} --> {n}")
    # expose click handlers and package data for interactive HTML
    for name, info in pkg_info.items():
        pid = sanitize_id(f"pkg_{name}")
        # note: click handlers already added in render_packages; also create summary JSON in HTML output
        parts.append(f"%% pkg_meta {name}")

    # store package_info for possible HTML export
    generated_pkg_info = pkg_info

    # Install-related detailed nodes
    install = data.get("install", {})
    reg_node, reg_id = render_registry_node(install.get("registry_entries", []))
    parts.append(reg_node)
    parts.append(f"{sanitize_id('install')} --> {reg_id}")

    env_node, env_id = render_env_vars_node(install.get("env_vars", []))
    parts.append(env_node)
    parts.append(f"{sanitize_id('install')} --> {env_id}")

    fa_node, fa_id = render_file_assocs_node(install.get("file_associations", []))
    parts.append(fa_node)
    parts.append(f"{sanitize_id('install')} --> {fa_id}")

    # Misc top-level blocks
    if data.get("signing"):
        s = data.get("signing", {})
        s_id = sanitize_id("signing")
        cert = s.get("certificate")
        ts = s.get("timestamp_url")
        label = "signing: enabled"
        if cert:
            label += f"<br>{cert.split('/')[-1]}"
        if ts:
            label += f"<br>{escape_label(ts, 60)}"
        parts.append(f'{s_id}["{escape_label(label, 200)}"]\n')
        parts.append(f"class {s_id} meta")
        parts.append(f"{app_id} --> {s_id}")
    if data.get("update"):
        u = data.get("update", {})
        u_id = sanitize_id("update")
        u_label = "update: enabled"
        if u.get("update_url"):
            u_label += f"<br>{escape_label(u.get('update_url'), 80)}"
        parts.append(f'{u_id}["{escape_label(u_label, 200)}"]\n')
        parts.append(f"class {u_id} meta")
        parts.append(f"{app_id} --> {u_id}")

    # if user requested HTML later, generated_pkg_info will be used; otherwise keep empty
    try:
        generated_pkg_info
    except NameError:
        generated_pkg_info = {}

    return "\n".join(parts) + "\n", generated_pkg_info


def generate_html(mermaid_src: str, pkg_info: dict) -> str:
    """Wrap mermaid source into a simple interactive HTML page.

    Features:
    - Mermaid rendering
    - Sidebar listing packages with click-to-show details
    - Toggle to hide optional packages
    """
    import json
    safe_pkg_json = json.dumps(pkg_info)
    template = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>ypack visualization</title>
  <script src="https://unpkg.com/mermaid@10/dist/mermaid.esm.min.mjs" type="module"></script>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; display:flex; gap:12px; }}
    #graph {{ width: 75%; }}
    #sidebar {{ width: 25%; padding:12px; border-left:1px solid #ddd; }}
    .pkg-item {{ cursor:pointer; padding:6px; border-bottom:1px solid #eee; }}
    .pkg-item:hover {{ background:#fafafa }}
    .highlight {{ stroke:#ff0000 !important; stroke-width:2px !important; }}
    .hidden {{ display:none !important; }}
  </style>
</head>
<body>
  <div id="graph">
    <div class="mermaid">
{MERMAID}
    </div>
  </div>
  <div id="sidebar">
    <h3>Packages</h3>
    <div><label><input type="checkbox" id="toggle-optional" checked> Show optional</label></div>
    <div id="pkg-list"></div>
    <hr>
    <div id="pkg-detail"><em>Click a package to see details</em></div>
  </div>
<script type="module">
  import mermaid from 'https://unpkg.com/mermaid@10/dist/mermaid.esm.min.mjs'
  mermaid.initialize({ startOnLoad: true });
  const pkgInfo = {PKGJSON};
  const list = document.getElementById('pkg-list');
  const detail = document.getElementById('pkg-detail');
  function renderPkgList() {
    list.innerHTML = '';
    Object.values(pkgInfo).forEach(p => {
      const div = document.createElement('div');
      div.className = 'pkg-item';
      div.textContent = p.name + (p.optional ? ' (optional)' : '') + (p.default ? ' (default)' : '');
      div.onclick = () => showPkg(p.name);
      list.appendChild(div);
    });
  }
  window.showPkg = function(name) {
    const p = pkgInfo[name];
    if (!p) return;
    let html = `<h4>${p.name}</h4>`;
    if (p.description) html += `<div>${p.description}</div>`;
    if (p.sources && p.sources.length) html += `<div><strong>Sources:</strong><ul>${p.sources.map(s=>`<li>${s}</li>`).join('')}</ul></div>`;
    if (p.post_install) html += `<div><strong>post_install:</strong><pre>${Array.isArray(p.post_install)?p.post_install.join('\n'):p.post_install}</pre></div>`;
    if (p.files && p.files.length) html += `<div><strong>Files:</strong><ul>${p.files.map(f=>`<li>${f.src}</li>`).join('')}</ul></div>`;
    detail.innerHTML = html;
    // highlight node in SVG
    const svg = document.querySelector('svg');
    if (!svg) return;
    // clear previous highlights
    svg.querySelectorAll('.highlight').forEach(n=>n.classList.remove('highlight'));
    // nodes are rendered with id like 'node-n_pkg_Name' -- try to find by id substring
    svg.querySelectorAll('[id]').forEach(el => { if (el.id && el.id.includes('n_pkg_'+name)) { el.classList.add('highlight'); } });
  }
  document.getElementById('toggle-optional').addEventListener('change', (ev) => {
    const on = ev.target.checked;
    const svg = document.querySelector('svg');
    if (!svg) return;
    Object.values(pkgInfo).forEach(p => {
      if (p.optional) {
        // nodes have class 'pkg_optional' so find elements with that class
        svg.querySelectorAll('.pkg_optional').forEach(el => { el.style.display = on ? '' : 'none'; });
      }
    });
  });
  renderPkgList();
</script>
</body>
</html>"""
    html = template.replace('{MERMAID}', mermaid_src).replace('{PKGJSON}', safe_pkg_json)
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Mermaid flowchart from a ypack YAML config")
    parser.add_argument("input", help="Input YAML file")
    parser.add_argument("-o", "--output", help="Output .mmd file (defaults to stdout)")
    parser.add_argument("--html", help="Also produce an interactive HTML file (provide path)")
    args = parser.parse_args(argv)

    with open(args.input, "rb") as fh:
        data = yaml.safe_load(fh) or {}

    mermaid, pkg_info = generate_mermaid(data)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(mermaid)
        print(f"Wrote Mermaid to {args.output}")
    else:
        sys.stdout.write(mermaid)

    if args.html:
        html = generate_html(mermaid, pkg_info)
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"Wrote interactive HTML to {args.html}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
