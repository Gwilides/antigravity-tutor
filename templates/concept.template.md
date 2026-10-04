---
id: "{{id}}"                        # Clean file slug (e.g. "goroutines") without domain prefix
title: "{{title}}"                  # Declarative Andy Matuschak thesis title (what was proven)
domain: "{{domain}}"                # Knowledge domain (e.g. "cs-foundations", "languages/go")
status: solid                       # solid | shaky
last_tested: "{{date}}"             # YYYY-MM-DD
interval_days: 3                    # Retention interval in days (progression: 3 -> 7 -> 16 -> 35 -> 90)

# Graph connections (Core 4 + refines)
depends_on:
  - "[[{{prerequisite_slug}}]]"
part_of:
  - "[[{{domain}}/_index]]"
contrasted_with:
  - "[[{{contrasted_slug}}]]"
solves:
  - "{{problem_solved}}"
refines: []
---

# {{title}}

### 1. Foundation (Unconditional Truths)
<!-- Unconditional truths, universal statements, and precise operational definitions that anchor the concept. -->
{{foundation_content}}

### 2. Motivation (What problem are we solving?)
<!-- The concrete tension, bottleneck, or historical impasse that forced this invention. -->
{{motivation_content}}

### 3. Derivation & Mechanism
<!-- Causal step-by-step derivation explaining how the mechanism works, with KaTeX formulas and diagrams. -->
{{derivation_content}}

### 4. Distinction & Pitfalls (What not to confuse it with?)
<!-- Contrasts with adjacent concepts and common traps/misconceptions to avoid. -->
- **In contrast to {{contrasted_concept}}:** {{distinction_content}}
- **Pitfall:** {{pitfall_content}}

### 5. Sessions
<!-- Wikilinks to sessions where this concept was introduced or verified. -->
- [[{{session_id}}]]
