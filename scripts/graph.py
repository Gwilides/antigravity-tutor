#!/usr/bin/env python3
"""
Antigravity Tutor — Graph Engine CLI
Knowledge Space Theory (KST) DAG engine, Tarjan/DFS cycle detection,
and active recall retention mechanics for Obsidian vault.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("[ERROR] PyYAML is required. Please install via: pip install pyyaml>=6.0\n")
    sys.exit(1)

# Markers for auto-generated section in domain _index.md
HORIZON_START = "<!-- AUTO-GENERATED HORIZON START -->"
HORIZON_END = "<!-- AUTO-GENERATED HORIZON END -->"

SERVICE_DIRS = {".obsidian", ".trash", ".git", ".agents", "__pycache__"}


@dataclass
class CardData:
    slug: str
    file_path: Path
    domain: str
    title: str
    status: str  # 'solid', 'shaky', 'ready', 'locked'
    last_tested: datetime.date | None
    interval_days: int
    depends_on: list[str] = field(default_factory=list)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def delta_t(self) -> int:
        if self.last_tested is None:
            return 0
        today = datetime.date.today()
        return max(0, (today - self.last_tested).days)

    @property
    def retention(self) -> float:
        # One-line exponential forgetting curve: R = 2 ** (- (delta_t / I))
        interval = max(1, self.interval_days)
        return 2.0 ** (-(self.delta_t / interval))


def normalize_slug(text: str) -> str:
    """Strip wikilinks, quotes, aliases, and whitespace: re.sub(r'[\\[\\]"\'\\s]', '', item)."""
    if not text:
        return ""
    # Strip Obsidian alias if present: [[slug|Alias]] -> slug
    target = text.split("|")[0]
    cleaned = re.sub(r'[\[\]"\'\s]', "", target)
    return cleaned.strip()


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and markdown body from file content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            try:
                data = yaml.safe_load(fm_text) or {}
                if isinstance(data, dict):
                    return data, body
            except Exception:
                pass
    return {}, content


def parse_date(val: Any) -> datetime.date | None:
    """Robustly parse date from YAML frontmatter."""
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip().strip('"').strip("'")
        try:
            return datetime.date.fromisoformat(val)
        except ValueError:
            return None
    return None


def resolve_vault_path(vault_arg: str | None) -> Path:
    """
    Resolve vault path using:
    1. CLI argument (--vault)
    2. config.json in cwd or repo root ('vault_path')
    3. Default fallback: ~/Documents/Obsidian/LearningVault
    Expands tilde (~) with os.path.expanduser().
    """
    if vault_arg:
        return Path(os.path.expanduser(vault_arg)).resolve()

    # Search config.json
    candidates = [
        Path.cwd() / "config.json",
        Path(__file__).resolve().parent.parent / "config.json",
    ]
    for config_path in candidates:
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if "vault_path" in cfg and cfg["vault_path"]:
                        return Path(os.path.expanduser(cfg["vault_path"])).resolve()
            except Exception:
                pass

    # Default fallback
    return Path(os.path.expanduser("~/Documents/Obsidian/LearningVault")).resolve()


def load_all_cards(knowledge_dir: Path) -> dict[str, CardData]:
    """
    Recursively scan knowledge_dir and load all concept cards.
    Ignores service directories (.obsidian, .trash, .git, etc.) and _index.md files.
    """
    cards: dict[str, CardData] = {}
    if not knowledge_dir.exists():
        return cards

    for root, dirs, files in os.walk(knowledge_dir):
        # Prune service directories
        dirs[:] = [d for d in dirs if d not in SERVICE_DIRS and not d.startswith(".")]

        rel_root = Path(root).relative_to(knowledge_dir)
        current_domain = str(rel_root).replace("\\", "/") if str(rel_root) != "." else "general"

        for file_name in files:
            if not file_name.endswith(".md") or file_name.startswith(".") or file_name == "_index.md":
                continue

            file_path = Path(root) / file_name
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                sys.stderr.write(f"[WARNING] Failed to read {file_path}: {e}\n")
                continue

            fm, body = parse_frontmatter(content)
            slug = fm.get("id") or file_path.stem
            slug = str(slug).strip()

            title = fm.get("title")
            if not title:
                # Extract first heading
                h_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
                title = h_match.group(1).strip() if h_match else slug

            card_domain = fm.get("domain") or current_domain
            status = str(fm.get("status", "solid")).strip().lower()
            last_tested = parse_date(fm.get("last_tested"))
            interval_days = int(fm.get("interval_days", 3))

            raw_deps = fm.get("depends_on") or []
            if isinstance(raw_deps, str):
                raw_deps = [raw_deps]
            deps = []
            for d in raw_deps:
                norm_d = normalize_slug(str(d))
                if norm_d:
                    deps.append(norm_d)

            card = CardData(
                slug=slug,
                file_path=file_path,
                domain=str(card_domain),
                title=str(title),
                status=status,
                last_tested=last_tested,
                interval_days=interval_days,
                depends_on=deps,
                raw_frontmatter=fm,
                body=body,
            )
            cards[slug] = card

    return cards


def parse_planned_curriculum(index_content: str) -> list[dict[str, Any]]:
    """
    Case-insensitive search for section containing 'Planned Curriculum' or 'Curriculum' in _index.md.
    Parses planned concepts with id/slug, depends_on, and optional title.
    """
    heading_match = re.search(r"(?im)^##+\s+.*(?:planned\s+curriculum|curriculum).*$", index_content)
    if not heading_match:
        return []

    start_pos = heading_match.end()
    end_match = re.search(
        r"(?im)(?:^##+\s+|<!--\s*AUTO-GENERATED\s*HORIZON\s*START\s*-->)",
        index_content[start_pos:],
    )
    section_text = (
        index_content[start_pos : start_pos + end_match.start()]
        if end_match
        else index_content[start_pos:]
    )

    items: list[dict[str, Any]] = []

    # First attempt: YAML parsing of bullet list
    list_lines = []
    in_list = False
    for line in section_text.splitlines():
        if line.strip().startswith("-"):
            in_list = True
        if in_list:
            list_lines.append(line)

    if list_lines:
        yaml_content = "\n".join(list_lines)
        try:
            parsed = yaml.safe_load(yaml_content)
            if isinstance(parsed, list):
                for entry in parsed:
                    if isinstance(entry, dict) and ("id" in entry or "slug" in entry):
                        node_id = normalize_slug(str(entry.get("id") or entry.get("slug")))
                        raw_deps = entry.get("depends_on") or []
                        if isinstance(raw_deps, str):
                            raw_deps = [raw_deps]
                        deps = [normalize_slug(str(d)) for d in raw_deps if normalize_slug(str(d))]
                        title = str(entry.get("title", node_id)).strip()
                        items.append({"id": node_id, "title": title, "depends_on": deps})
        except Exception:
            pass

    # Fallback attempt: regex pattern matching
    if not items:
        # Match - id: <slug> blocks
        pattern = re.compile(
            r"-\s+id:\s*([^\n\r]+?)(?:\n\s+title:\s*[\"']?([^\n\r\"']+)[\"']?)?(?:\n\s+depends_on:\s*(\[[^\]]*\]|[^\n\r]+))?",
            re.MULTILINE,
        )
        for m in pattern.finditer(section_text):
            node_id = normalize_slug(m.group(1))
            if not node_id:
                continue
            title = m.group(2).strip() if m.group(2) else node_id
            raw_deps_str = m.group(3) or ""
            deps = []
            if raw_deps_str:
                raw_deps_str = raw_deps_str.strip().lstrip("[").rstrip("]")
                for d in raw_deps_str.split(","):
                    clean_d = normalize_slug(d)
                    if clean_d:
                        deps.append(clean_d)
            items.append({"id": node_id, "title": title, "depends_on": deps})

    return items


def detect_cycles_dfs(graph: dict[str, list[str]]) -> list[str] | None:
    """
    Detect cycles in directed graph using DFS.
    Returns cycle chain as list of node strings (e.g. ['A', 'B', 'A']) if found, else None.
    """
    visited: dict[str, int] = {}  # 0: unvisited, 1: visiting (on stack), 2: visited

    def dfs(node: str, path: list[str]) -> list[str] | None:
        visited[node] = 1
        for dep in graph.get(node, []):
            if visited.get(dep, 0) == 1:
                # Cycle detected
                cycle_start_idx = path.index(dep) if dep in path else 0
                return path[cycle_start_idx:] + [dep]
            elif visited.get(dep, 0) == 0:
                res = dfs(dep, path + [dep])
                if res is not None:
                    return res
        visited[node] = 2
        return None

    for node in sorted(graph.keys()):
        if visited.get(node, 0) == 0:
            cycle = dfs(node, [node])
            if cycle is not None:
                return cycle
    return None


def calculate_kst_frontier(
    domain_slugs: set[str],
    all_cards: dict[str, CardData],
    planned_items: dict[str, dict[str, Any]],
    graph_deps: dict[str, list[str]],
) -> tuple[list[str], list[str], list[str], list[str], dict[str, str]]:
    """
    Calculate Knowledge Space Theory (KST) Frontier:
    1. Mastered Foundation: Solid nodes that are not immediate prerequisites of Ready topics.
    2. Inner Fringe: Solid nodes that are immediate prerequisites of Ready topics.
    3. Outer Fringe: Ready topics (unmastered topics whose dependencies are all solid).
    4. Next Horizon: Locked topics (unmastered topics with at least one non-solid dependency).
    Returns (mastered, inner_fringe, outer_fringe, locked, status_map).
    """
    status_map: dict[str, str] = {}

    # Initial classification
    for slug in domain_slugs:
        if slug in all_cards:
            status_map[slug] = all_cards[slug].status  # 'solid' or 'shaky'
        else:
            # Check dependencies
            deps = graph_deps.get(slug, [])
            if not deps:
                status_map[slug] = "ready"
            else:
                all_deps_solid = True
                for dep in deps:
                    dep_status = all_cards.get(dep, None)
                    if dep_status is None or dep_status.status != "solid":
                        all_deps_solid = False
                        break
                status_map[slug] = "ready" if all_deps_solid else "locked"

    outer_fringe: list[str] = []
    locked: list[str] = []
    solid_nodes: list[str] = []

    for slug in sorted(domain_slugs):
        st = status_map[slug]
        if st == "ready":
            outer_fringe.append(slug)
        elif st == "locked":
            locked.append(slug)
        elif st == "shaky":
            # Shaky nodes on disk are also part of active frontier for review
            outer_fringe.append(slug)
        elif st == "solid":
            solid_nodes.append(slug)

    # Determine Inner Fringe: solid nodes that are direct parents of any Outer Fringe node
    inner_fringe_set: set[str] = set()
    for ready_node in outer_fringe:
        for dep in graph_deps.get(ready_node, []):
            if dep in status_map and status_map[dep] == "solid":
                inner_fringe_set.add(dep)
            elif dep in all_cards and all_cards[dep].status == "solid":
                inner_fringe_set.add(dep)

    inner_fringe = sorted(inner_fringe_set)
    mastered = [s for s in solid_nodes if s not in inner_fringe_set]

    return mastered, inner_fringe, outer_fringe, locked, status_map


def sanitize_node_id(slug: str) -> str:
    """Generate safe Mermaid node ID."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", slug)
    return f"node_{clean}"


def generate_mermaid_dag(
    mastered: list[str],
    inner_fringe: list[str],
    outer_fringe: list[str],
    locked: list[str],
    graph_deps: dict[str, list[str]],
    titles: dict[str, str],
    is_russian: bool = True,
) -> str:
    """
    Generate compact Mermaid DAG (max 10-15 nodes) with clean node labels.
    No wikilinks inside labels: id["Label (Status)"].
    """
    lines = ["```mermaid", "graph TD"]

    # Subgraph headers
    sg_mastered = "Освоенный фундамент" if is_russian else "Mastered Foundation"
    sg_inner = "Inner Fringe (Опора)" if is_russian else "Inner Fringe (Prerequisites)"
    sg_outer = "Outer Fringe (Готово к изучению)" if is_russian else "Outer Fringe (Ready)"
    sg_next = "Next Step (Перспектива)" if is_russian else "Next Step (Locked)"

    edges: list[tuple[str, str]] = []

    # 1. Mastered Foundation (deep foundation)
    if mastered:
        lines.append(f'    subgraph "{sg_mastered}"')
        if len(mastered) > 2:
            # Collapse deep foundation into a single summary node
            fdn_id = "foundation_base"
            label = (
                f"Базовый фундамент ({len(mastered)} тем) (Solid)"
                if is_russian
                else f"Mastered Foundation ({len(mastered)} topics) (Solid)"
            )
            lines.append(f'        {fdn_id}["{label}"]')
            # Connect summary node to inner fringe nodes that depend on any mastered node
            for inner in inner_fringe:
                if any(m in graph_deps.get(inner, []) for m in mastered):
                    edges.append((fdn_id, sanitize_node_id(inner)))
        else:
            for m in mastered:
                m_id = sanitize_node_id(m)
                lines.append(f'        {m_id}["{m} (Solid)"]')
                for inner in inner_fringe:
                    if m in graph_deps.get(inner, []):
                        edges.append((m_id, sanitize_node_id(inner)))
        lines.append("    end")

    # 2. Inner Fringe
    if inner_fringe:
        lines.append(f'    subgraph "{sg_inner}"')
        for inf in inner_fringe:
            inf_id = sanitize_node_id(inf)
            lines.append(f'        {inf_id}["{inf} (Solid)"]')
        lines.append("    end")

    # 3. Outer Fringe
    if outer_fringe:
        lines.append(f'    subgraph "{sg_outer}"')
        for out in outer_fringe:
            out_id = sanitize_node_id(out)
            label = f"{out} (Ready)"
            lines.append(f'        {out_id}["{label}"]')
            for dep in graph_deps.get(out, []):
                if dep in inner_fringe:
                    edges.append((sanitize_node_id(dep), out_id))
                elif dep in mastered and len(mastered) <= 2:
                    edges.append((sanitize_node_id(dep), out_id))
        lines.append("    end")

    # 4. Next Step (Locked) — capped so total nodes in diagram <= 15
    active_count = len(lines) - 2  # Approximate count
    max_locked_to_show = max(1, 15 - len(mastered[:1]) - len(inner_fringe) - len(outer_fringe))
    selected_locked = locked[:max_locked_to_show]

    if selected_locked:
        lines.append(f'    subgraph "{sg_next}"')
        for loc in selected_locked:
            loc_id = sanitize_node_id(loc)
            lines.append(f'        {loc_id}["{loc} (Locked)"]')
            for dep in graph_deps.get(loc, []):
                if dep in outer_fringe:
                    edges.append((sanitize_node_id(dep), loc_id))
                elif dep in inner_fringe:
                    edges.append((sanitize_node_id(dep), loc_id))
        lines.append("    end")

    # Append edges
    if edges:
        lines.append("")
        for src, dst in sorted(set(edges)):
            lines.append(f"    {src} --> {dst}")

    lines.append("```")
    return "\n".join(lines)


def generate_concept_registry(
    all_slugs: list[str],
    titles: dict[str, str],
    status_map: dict[str, str],
    is_russian: bool = True,
) -> str:
    """Generate Concept Registry lines for _index.md."""
    heading = "## 3. Реестр концептов домена" if is_russian else "## 3. Domain Concept Registry"
    lines = [heading]

    status_priority = {"solid": 0, "shaky": 1, "ready": 2, "locked": 3}
    sorted_slugs = sorted(
        all_slugs,
        key=lambda s: (status_priority.get(status_map.get(s, "locked"), 99), s),
    )

    for slug in sorted_slugs:
        title = titles.get(slug, slug)
        raw_status = status_map.get(slug, "locked")
        status_tag = f"[{raw_status.capitalize()}]"
        lines.append(f"- [[{slug}]] — {title} `{status_tag}`")

    return "\n".join(lines)


def sync_domain(vault_path: Path, domain: str) -> None:
    """
    Synchronize knowledge graph for a single domain.
    1. Scan frontmatter in <vault_path>/knowledge/.
    2. Parse Planned Curriculum from _index.md.
    3. Tarjan/DFS cycle detection.
    4. Calculate KST frontier.
    5. Generate compact Mermaid DAG and update _index.md.
    """
    knowledge_dir = vault_path / "knowledge"
    domain_dir = knowledge_dir / domain
    index_file = domain_dir / "_index.md"

    # Cold start: create directory and _index.md if missing
    if not domain_dir.exists():
        domain_dir.mkdir(parents=True, exist_ok=True)

    if not index_file.exists():
        template_file = (
            Path(__file__).resolve().parent.parent / "templates" / "domain_index.template.md"
        )
        if template_file.is_file():
            try:
                with open(template_file, "r", encoding="utf-8") as tf:
                    init_content = tf.read().replace("{{domain}}", domain)
            except Exception:
                init_content = ""
        else:
            init_content = f"""---
domain: {domain}
title: "Карта знаний: {domain}"
---

# Карта знаний: {domain}

## 1. Дорожная карта раздела (Planned Curriculum)
<!-- Добавьте планируемые концепты здесь -->

{HORIZON_START}
{HORIZON_END}
"""
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(init_content)

    # Read _index.md
    with open(index_file, "r", encoding="utf-8") as f:
        index_content = f.read()

    is_russian = bool(re.search(r"[\u0400-\u04FF]", index_content))

    # 1. Scan cards in knowledge
    all_cards = load_all_cards(knowledge_dir)
    domain_cards = {
        s: c for s, c in all_cards.items() if c.domain == domain or c.file_path.parent == domain_dir
    }

    # 2. Parse Planned Curriculum from _index.md
    planned_items = parse_planned_curriculum(index_content)
    planned_dict = {item["id"]: item for item in planned_items}

    # Gather domain slugs
    domain_slugs = set(domain_cards.keys()).union(set(planned_dict.keys()))

    # Build dependency graph
    graph_deps: dict[str, list[str]] = {}
    titles: dict[str, str] = {}

    for slug in domain_slugs:
        if slug in domain_cards:
            card = domain_cards[slug]
            graph_deps[slug] = list(card.depends_on)
            titles[slug] = card.title
        else:
            p_item = planned_dict[slug]
            graph_deps[slug] = list(p_item.get("depends_on", []))
            titles[slug] = p_item.get("title", slug)

    # Handle dangling dependencies
    for node, deps in list(graph_deps.items()):
        for dep in deps:
            if dep not in all_cards and dep not in domain_slugs:
                sys.stderr.write(
                    f"[WARNING] Dangling dependency: '{dep}' referenced by '{node}' not found on disk. Treating as virtual (Locked) node.\n"
                )
                if dep not in graph_deps:
                    graph_deps[dep] = []
                    titles[dep] = dep

    # 3. Tarjan/DFS cycle detection BEFORE modifying _index.md
    # Full graph for cycle check includes domain nodes and their dependencies
    cycle_check_graph: dict[str, list[str]] = {}
    for node in graph_deps:
        cycle_check_graph[node] = list(graph_deps.get(node, []))
    for slug, card in all_cards.items():
        if slug not in cycle_check_graph:
            cycle_check_graph[slug] = list(card.depends_on)

    cycle = detect_cycles_dfs(cycle_check_graph)
    if cycle is not None:
        cycle_str = " -> ".join(cycle)
        sys.stderr.write(f"[ERROR] Dependency cycle: {cycle_str}\n")
        sys.exit(1)

    # 4. Calculate KST Frontier
    mastered, inner_fringe, outer_fringe, locked, status_map = calculate_kst_frontier(
        domain_slugs, all_cards, planned_dict, graph_deps
    )

    # 5. Generate compact Mermaid DAG
    mermaid_dag = generate_mermaid_dag(
        mastered, inner_fringe, outer_fringe, locked, graph_deps, titles, is_russian
    )

    # 6. Generate Concept Registry
    registry_text = generate_concept_registry(
        list(domain_slugs), titles, status_map, is_russian
    )

    frontier_heading = (
        "## 2. Активный горизонт графа (Frontier DAG)"
        if is_russian
        else "## 2. Active Frontier DAG"
    )

    generated_block = f"""{HORIZON_START}
{frontier_heading}
{mermaid_dag}

{registry_text}
{HORIZON_END}"""

    # 7. Write between markers in _index.md
    if HORIZON_START in index_content and HORIZON_END in index_content:
        start_idx = index_content.find(HORIZON_START)
        end_idx = index_content.find(HORIZON_END) + len(HORIZON_END)
        new_content = index_content[:start_idx] + generated_block + index_content[end_idx:]
    else:
        new_content = index_content.rstrip() + "\n\n" + generated_block + "\n"

    with open(index_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[SUCCESS] Synchronized domain '{domain}' -> {index_file}")
    print(
        f"  Frontier: {len(mastered)} Mastered, {len(inner_fringe)} Inner Fringe, {len(outer_fringe)} Ready, {len(locked)} Locked"
    )


def progress_interval(current_i: int) -> int:
    """
    Stepwise interval progression on success (solid):
    [3 -> 7 -> 16 -> 35 -> 90], or if >= 90: round(I * 2.2).
    """
    steps = [3, 7, 16, 35, 90]
    for step in steps:
        if current_i < step:
            return step
    return round(current_i * 2.2)


def update_frontmatter_in_file(
    file_path: Path,
    updates: dict[str, Any],
) -> None:
    """
    Surgically update YAML frontmatter fields in a markdown file,
    preserving comments, body, and structure.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        # Wrap with frontmatter if absent
        fm_lines = ["---"]
        for k, v in updates.items():
            fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")
        new_content = "\n".join(fm_lines) + "\n\n" + content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return

    parts = content.split("---", 2)
    fm_text = parts[1]
    body = parts[2] if len(parts) >= 3 else ""

    fm_lines = fm_text.splitlines()
    keys_updated = set()

    new_fm_lines = []
    for line in fm_lines:
        matched_key = None
        for key in updates:
            if re.match(rf"^\s*{re.escape(key)}\s*:", line):
                matched_key = key
                break
        if matched_key:
            new_fm_lines.append(f"{matched_key}: {updates[matched_key]}")
            keys_updated.add(matched_key)
        else:
            new_fm_lines.append(line)

    # Append any keys that didn't already exist
    for key, val in updates.items():
        if key not in keys_updated:
            new_fm_lines.append(f"{key}: {val}")

    new_content = "---\n" + "\n".join(new_fm_lines) + "\n---" + body
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def cmd_sync(args: argparse.Namespace) -> None:
    vault_path = resolve_vault_path(args.vault)
    knowledge_dir = vault_path / "knowledge"

    if args.domain:
        sync_domain(vault_path, args.domain)
    else:
        # Find all domains
        if not knowledge_dir.exists():
            print(f"[INFO] Knowledge directory {knowledge_dir} does not exist yet. Creating...")
            knowledge_dir.mkdir(parents=True, exist_ok=True)
            return

        domains: set[str] = set()
        for root, dirs, files in os.walk(knowledge_dir):
            dirs[:] = [d for d in dirs if d not in SERVICE_DIRS and not d.startswith(".")]
            rel = Path(root).relative_to(knowledge_dir)
            if str(rel) != "." and ("_index.md" in files or any(f.endswith(".md") for f in files)):
                domains.add(str(rel).replace("\\", "/"))

        if not domains:
            print("[INFO] No domain folders found in knowledge directory.")
            return

        for domain in sorted(domains):
            sync_domain(vault_path, domain)


def cmd_refresh(args: argparse.Namespace) -> None:
    """
    Select 3-5 cards for active recall refresh:
    - R = 2 ** (- (delta_t / I))
    - Priority window 0.4 <= R <= 0.6, weighted by hub score.
    - Review Cap: strictly 3-5 cards.
    - Amnesia protocol check: max delta_t > 30 days.
    """
    vault_path = resolve_vault_path(args.vault)
    knowledge_dir = vault_path / "knowledge"

    all_cards = load_all_cards(knowledge_dir)
    if not all_cards:
        print("[INFO] No concept cards found in vault.")
        return

    # Filter by domain if specified
    if args.domain:
        cards = [c for c in all_cards.values() if c.domain == args.domain]
        if not cards:
            print(f"[INFO] No concept cards found for domain '{args.domain}'.")
            return
    else:
        cards = list(all_cards.values())

    # Calculate hub scores across vault: count incoming dependencies
    hub_scores: dict[str, int] = {slug: 0 for slug in all_cards}
    for card in all_cards.values():
        for dep in card.depends_on:
            if dep in hub_scores:
                hub_scores[dep] += 1

    # Amnesia protocol check
    max_delta_t = max((c.delta_t for c in cards), default=0)
    if max_delta_t > 30:
        print(
            f"\n⚠️  [AMNESIA PROTOCOL ALERT] Long hiatus detected: max inactive interval is {max_delta_t} days (> 30 days)."
        )
        print(
            "   Recommendation: Begin with 1–2 gentle macro review questions before diving into granular cards.\n"
        )

    # Categorize cards for active recall ranking
    # Window: 0.4 <= R <= 0.6 (Optimal recall window)
    tier1: list[CardData] = []  # In sweet spot
    tier2: list[CardData] = []  # Overdue (R < 0.4)
    tier3: list[CardData] = []  # Fresh (R > 0.6)

    for c in cards:
        r = c.retention
        if 0.4 <= r <= 0.6:
            tier1.append(c)
        elif r < 0.4:
            tier2.append(c)
        else:
            tier3.append(c)

    # Sort tier1 by highest hub score, then distance to 0.5
    tier1.sort(key=lambda c: (-hub_scores.get(c.slug, 0), abs(c.retention - 0.5)))
    # Sort tier2 by highest hub score, then lowest retention
    tier2.sort(key=lambda c: (-hub_scores.get(c.slug, 0), c.retention))
    # Sort tier3 by highest hub score, then lowest retention
    tier3.sort(key=lambda c: (-hub_scores.get(c.slug, 0), c.retention))

    candidates = tier1 + tier2 + tier3

    # Review Cap: strictly 3-5 cards
    n_cards = len(candidates)
    if n_cards >= 5:
        target_count = 5
    elif n_cards >= 3:
        target_count = n_cards
    else:
        target_count = n_cards

    selected = candidates[:target_count]

    print(f"============================================================")
    print(f"Active Recall Refresh Queue (Cap: 3–5 cards | Selected: {len(selected)})")
    print(f"============================================================")

    for i, c in enumerate(selected, start=1):
        r = c.retention
        h = hub_scores.get(c.slug, 0)
        dt = c.delta_t
        iv = c.interval_days

        if 0.4 <= r <= 0.6:
            rec = "Optimal recall window (40-60% retention)"
        elif r < 0.4:
            rec = "Urgent: Decayed memory (retention below 40%)"
        else:
            rec = "Maintenance: Proactive reinforcement (retention above 60%)"

        if h >= 2:
            rec += f" [Key Hub: {h} dependent cards]"

        print(f"\n{i}. [{c.slug}] \"{c.title}\"")
        print(f"   Domain: {c.domain}")
        print(f"   Δt: {dt} days | Interval (I): {iv} days | Retention (R): {r:.2f} ({r * 100:.1f}%)")
        print(f"   Hub Score: {h} incoming dependencies")
        print(f"   Recommendation: {rec}")


def cmd_status(args: argparse.Namespace) -> None:
    """Output summary: total concepts per domain, active frontier (Ready topics), retention stats."""
    vault_path = resolve_vault_path(args.vault)
    knowledge_dir = vault_path / "knowledge"

    all_cards = load_all_cards(knowledge_dir)

    # Discover domains
    domains: set[str] = set()
    if knowledge_dir.exists():
        for root, dirs, files in os.walk(knowledge_dir):
            dirs[:] = [d for d in dirs if d not in SERVICE_DIRS and not d.startswith(".")]
            rel = Path(root).relative_to(knowledge_dir)
            if str(rel) != "." and ("_index.md" in files or any(f.endswith(".md") for f in files)):
                domains.add(str(rel).replace("\\", "/"))

    print("============================================================")
    print("Antigravity Tutor — Knowledge Frontier Status")
    print(f"Vault: {vault_path}")
    print("============================================================")

    total_crystallized = len(all_cards)
    total_ready = 0
    max_vault_delta_t = 0

    if not domains and not all_cards:
        print("Vault is empty. No domains or concepts registered yet.")
        return

    for domain in sorted(domains):
        domain_dir = knowledge_dir / domain
        index_file = domain_dir / "_index.md"

        d_cards = {
            s: c for s, c in all_cards.items() if c.domain == domain or c.file_path.parent == domain_dir
        }
        solid_count = sum(1 for c in d_cards.values() if c.status == "solid")
        shaky_count = sum(1 for c in d_cards.values() if c.status == "shaky")

        planned_items: list[dict[str, Any]] = []
        if index_file.is_file():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    planned_items = parse_planned_curriculum(f.read())
            except Exception:
                pass

        planned_dict = {item["id"]: item for item in planned_items}
        domain_slugs = set(d_cards.keys()).union(set(planned_dict.keys()))

        graph_deps: dict[str, list[str]] = {}
        for slug in domain_slugs:
            if slug in d_cards:
                graph_deps[slug] = list(d_cards[slug].depends_on)
            else:
                graph_deps[slug] = list(planned_dict[slug].get("depends_on", []))

        _, _, outer_fringe, locked, _ = calculate_kst_frontier(
            domain_slugs, all_cards, planned_dict, graph_deps
        )

        total_ready += len(outer_fringe)

        # Retention stats
        retentions = [c.retention for c in d_cards.values()]
        avg_r = (sum(retentions) / len(retentions)) if retentions else 1.0
        optimal_cnt = sum(1 for r in retentions if 0.4 <= r <= 0.6)
        overdue_cnt = sum(1 for r in retentions if r < 0.4)
        d_max_dt = max((c.delta_t for c in d_cards.values()), default=0)
        max_vault_delta_t = max(max_vault_delta_t, d_max_dt)

        print(f"\n📂 Domain: {domain}")
        print(f"   Crystallized Cards: {len(d_cards)} (Solid: {solid_count}, Shaky: {shaky_count})")
        print(f"   Planned Topics:     {len(planned_dict)} (Ready: {len(outer_fringe)}, Locked: {len(locked)})")
        print(f"   Frontier (Ready):   {', '.join(outer_fringe) if outer_fringe else 'None'}")
        print(
            f"   Retention Health:   Avg R: {avg_r:.2f} | Optimal: {optimal_cnt} | Overdue: {overdue_cnt} | Max Inactive: {d_max_dt}d"
        )

    print("\n------------------------------------------------------------")
    print(f"Vault Totals: {total_crystallized} Crystallized Concepts | {total_ready} Ready Topics on Frontier")

    if max_vault_delta_t > 30:
        print(
            f"⚠️  [AMNESIA PROTOCOL ALERT] Long hiatus detected: {max_vault_delta_t} days since last session (> 30 days)."
        )


def cmd_new_session(args: argparse.Namespace) -> None:
    """
    Create <vault_path>/sessions/YYYY-MM-DD-<slug>.md with frontmatter status: in_progress.
    """
    vault_path = resolve_vault_path(args.vault)
    sessions_dir = vault_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    topic = args.topic.strip()
    topic_slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic).strip("-").lower()
    domain = args.domain or "general"

    session_filename = f"{today_str}-{topic_slug}.md"
    session_file = sessions_dir / session_filename

    # Check for template
    template_file = (
        Path(__file__).resolve().parent.parent / "templates" / "session.template.md"
    )
    if template_file.is_file():
        try:
            with open(template_file, "r", encoding="utf-8") as tf:
                content = (
                    tf.read()
                    .replace("{{id}}", f"{today_str}-{topic_slug}")
                    .replace("{{date}}", today_str)
                    .replace("{{domain}}", domain)
                    .replace("{{topic}}", topic)
                    .replace("{{topic_slug}}", topic_slug)
                )
        except Exception:
            content = ""
    else:
        content = f"""---
id: {today_str}-{topic_slug}
date: {today_str}
domain: {domain}
status: in_progress
target_concepts:
  - "[[{topic_slug}]]"
---

# Session: {topic}

> [!abstract] Overview
> Socratic learning session on {topic}.

<!-- Live Mirroring content appends below -->
"""

    with open(session_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SUCCESS] Created session: {session_file}")


def cmd_update_card(args: argparse.Namespace) -> None:
    """
    Helper to update card frontmatter:
    - updates last_tested to today
    - adjusts status to solid or shaky
    - updates interval_days (advances stepwise or resets to 1)
    - updates 1st-order FIRe on parents
    """
    vault_path = resolve_vault_path(args.vault)
    knowledge_dir = vault_path / "knowledge"

    all_cards = load_all_cards(knowledge_dir)
    target_slug = normalize_slug(args.slug)

    card = all_cards.get(target_slug)
    if not card:
        sys.stderr.write(f"[ERROR] Card '{target_slug}' not found in knowledge vault.\n")
        sys.exit(1)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    old_status = card.status
    old_interval = card.interval_days

    if args.result == "solid":
        new_status = "solid"
        new_interval = progress_interval(old_interval)
    else:
        new_status = "shaky"
        new_interval = 1

    # Update card frontmatter
    update_frontmatter_in_file(
        card.file_path,
        {
            "status": new_status,
            "last_tested": today_str,
            "interval_days": new_interval,
        },
    )

    print(f"[SUCCESS] Updated card '{target_slug}':")
    print(f"  Status: {old_status} -> {new_status}")
    print(f"  Interval: {old_interval}d -> {new_interval}d")
    print(f"  Last tested: {today_str}")

    # Practical 1st-Order FIRe: update last_tested on all immediate parents
    fire_updated: list[str] = []
    for parent_slug in card.depends_on:
        parent_card = all_cards.get(parent_slug)
        if parent_card and parent_card.file_path.is_file():
            update_frontmatter_in_file(
                parent_card.file_path,
                {"last_tested": today_str},
            )
            fire_updated.append(parent_slug)

    if fire_updated:
        print(f"  1st-Order FIRe updated on parents: {', '.join(fire_updated)} (last_tested: {today_str})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Tutor — Graph Engine CLI")
    parser.add_argument("--vault", type=str, default=None, help="Path to Obsidian vault")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    sync_p = subparsers.add_parser("sync", help="Synchronize knowledge graph and horizon in _index.md")
    sync_p.add_argument("--domain", type=str, default=None, help="Target domain (e.g. languages/go)")
    sync_p.add_argument("--vault", type=str, default=argparse.SUPPRESS, help="Path to Obsidian vault")

    # refresh
    refresh_p = subparsers.add_parser("refresh", help="Select cards for active recall refresh")
    refresh_p.add_argument("--domain", type=str, default=None, help="Target domain (optional)")
    refresh_p.add_argument("--vault", type=str, default=argparse.SUPPRESS, help="Path to Obsidian vault")

    # status
    status_p = subparsers.add_parser("status", help="Display knowledge frontier and retention summary")
    status_p.add_argument("--vault", type=str, default=argparse.SUPPRESS, help="Path to Obsidian vault")

    # new-session
    session_p = subparsers.add_parser("new-session", help="Create a new learning session note")
    session_p.add_argument("--topic", type=str, required=True, help="Topic of the session")
    session_p.add_argument("--domain", type=str, default=None, help="Target domain")
    session_p.add_argument("--vault", type=str, default=argparse.SUPPRESS, help="Path to Obsidian vault")

    # update-card
    update_p = subparsers.add_parser("update-card", help="Update card review status and apply 1st-order FIRe")
    update_p.add_argument("--slug", type=str, required=True, help="Card slug")
    update_p.add_argument("--domain", type=str, default=None, help="Domain of card (optional)")
    update_p.add_argument("--result", choices=["solid", "shaky"], required=True, help="Review result")
    update_p.add_argument("--vault", type=str, default=argparse.SUPPRESS, help="Path to Obsidian vault")

    args = parser.parse_args()

    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "refresh":
        cmd_refresh(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "new-session":
        cmd_new_session(args)
    elif args.command == "update-card":
        cmd_update_card(args)


if __name__ == "__main__":
    main()
