---
domain: "{{domain}}"
title: "Knowledge Atlas: {{domain}}"
---

# Knowledge Atlas: {{domain}}

## 1. Planned Curriculum
- id: foundational-concept
  title: "Foundational principles establish unambiguous ground truths"
  depends_on: []
- id: derived-concept
  title: "Derived mechanisms resolve concrete tensions from foundations"
  depends_on: [foundational-concept]
- id: advanced-concept
  title: "Advanced architecture refining derived mechanisms"
  depends_on: [derived-concept]

<!-- AUTO-GENERATED HORIZON START -->
## 2. Active Frontier DAG
```mermaid
graph TD
    subgraph "Mastered Foundation"
        F0["Foundational Root (Solid)"]
    end

    subgraph "Inner Fringe (Prerequisites)"
        F0 --> P1["Prerequisite Node (Solid)"]
    end

    subgraph "Outer Fringe (Ready to Learn)"
        P1 --> R1["Target Concept (Ready)"]
    end

    subgraph "Next Step (Perspective)"
        R1 --> L1["Advanced Concept (Locked)"]
    end
```

## 3. Domain Concepts Registry
<!-- Synchronized automatically by scripts/graph.py sync -->
- [[foundational-concept]] — Foundational principles establish unambiguous ground truths `[Ready]`
- [[derived-concept]] — Derived mechanism solving concrete limitations of foundational concept `[Locked]`
- [[advanced-concept]] — Advanced architecture refining derived mechanisms `[Locked]`
<!-- AUTO-GENERATED HORIZON END -->
