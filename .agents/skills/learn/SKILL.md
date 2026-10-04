---
name: learn
description: >-
  Command routing and session orchestration engine for Antigravity Tutor.
  Handles user slash commands (/teach, /study, /refresh, /status), coordinates the 5-minute
  active recall workouts with Hub Priority and amnesia protocols, and interfaces with scripts/graph.py.
---

# Command Orchestration Engine (`learn`)

This skill defines the command dispatch, session orchestration, and active recall engine for **Antigravity Tutor**. It serves as the primary operational gateway bridging user commands into pedagogical execution, knowledge visualization, and persistent graph maintenance.

---

## 1. Overview & Architectural Role

Antigravity Tutor is an autonomous personal deep-learning mentor. The `learn` skill functions as the **Session Orchestrator**, translating high-level user commands into targeted, non-blocking workflows:

```mermaid
flowchart TD
    User(["User Input / Slash Command"]) --> Router{"learn Router"}

    Router -->|"/teach <topic>" or "/study"| TeachHandler["Session Init (graph.py new-session)\n+ teach skill (5 Phases)"]
    Router -->|"/refresh [domain]"| RefreshHandler["Active Recall Workout (5 min cap)\n• Amnesia check (>30d)\n• Hub Priority (3-5 cards)\n• graph.py update-card"]
    Router -->|"/status"| StatusHandler["Knowledge Frontier Report\n• graph.py status\n• Outer Fringe (Ready)\n• Next Action Recommendation"]
    Router -->|"Unrecognized / Freeform"| IntentCheck{"Is it a learning intent?"}

    IntentCheck -->|Yes| TeachHandler
    IntentCheck -->|No| SocraticGuide["Socratic Guidance / Help"]

    TeachHandler -.-> TeachSkill[".agents/skills/teach/SKILL.md"]
    TeachHandler -.-> VisualizeSkill[".agents/skills/visualize/SKILL.md"]
    RefreshHandler -.-> GraphCLI["scripts/graph.py"]
    StatusHandler -.-> GraphCLI
```

### Core Design Principles
1. **Zero Review Hell:** Active recall (`/refresh`) is 100% voluntary, strictly capped at 3–5 cards (~5 minutes), and prioritizes high-impact topological hubs. The user never faces an overwhelming backlog of hundreds of overdue cards.
2. **Frictionless Handoff:** Commands transition immediately into action without administrative delays or unnecessary approval gates.
3. **Decoupled Architecture:** User knowledge lives in an external Obsidian Vault, completely separated from repository code. All state operations pass through standardized CLI commands or semantic note operations.
4. **Pedagogical Integrity:** Whether teaching a brand new concept or refreshing an older one, explanations adhere to Grant Sanderson's motivated discovery, Amos Blomqvist's derivation chains, and Andy Matuschak's evergreen thesis structure.

---

## 2. Vault Path Resolution Protocol

All user notes (both session journals and crystallized concept cards) reside in an external Obsidian Vault configured via `config.json`.

### Path Resolution Algorithm
1. **Check Workspace Config:**
   - Look for `config.json` in the root of the workspace (`/home/gwilides/Projects/antigravity-tutor/config.json`).
   - If present, parse the JSON and extract the `"vault_path"` field.
2. **Path Expansion:**
   - Always expand the tilde (`~`) to the user's home directory (e.g., `os.path.expanduser(vault_path)` or `Path(vault_path).expanduser().resolve()`).
3. **Fallback Prompt (First Run / Missing Config):**
   - If `config.json` does not exist or `"vault_path"` is missing:
     - Prompt the user to provide their Obsidian Vault path or accept the default `~/Documents/Obsidian/LearningVault`.
     - Write the resolved configuration to `config.json` in the workspace root:
       ```json
       {
         "vault_path": "~/Documents/Obsidian/LearningVault"
       }
       ```
     - **CRITICAL:** `config.json` is listed in `.gitignore` and must **NEVER** be committed to Git.
4. **Two-Tier Directory Layout:**
   - **Tier 1: Stream (`<vault_path>/sessions/`):**
     * Contains live session journals named `YYYY-MM-DD-<topic-slug>.md`.
     * Tracks ephemeral learning processes, live reasoning steps, dialog, and immediate quiz logs.
     * Frontmatter lifecycle: `status: in_progress` $\to$ `status: completed` (or `status: paused`).
   - **Tier 2: Garden (`<vault_path>/knowledge/`):**
     * Contains timeless, low-entropy concept cards organized by domain: `<vault_path>/knowledge/<domain>/<concept-slug>.md`.
     * Contains domain atlas maps: `<vault_path>/knowledge/<domain>/_index.md`.
5. **Just-In-Time (JIT) Creation:**
   - Never pre-populate empty ghost directories. Create domain subdirectories and `_index.md` files dynamically upon crystallizing the first card in that domain.

---

## 3. Command Handlers

### 3.1 `/teach <topic>` (Alias: `/study <topic>`)

Initiates or resumes a structured deep-learning session on the target topic.

#### Step 1: Input Parsing
* Extract `<topic>` and optional domain qualifier from user input:
  - Format A: `/teach goroutines` $\to$ topic = `"goroutines"`, domain = auto-detect or `"general"`.
  - Format B: `/teach languages/go:goroutines` or `/teach goroutines in languages/go` $\to$ topic = `"goroutines"`, domain = `"languages/go"`.
  - Format C: Plain `/study <topic>` is treated identically to `/teach <topic>`.

#### Step 2: Unfinished Session Check & Creation
* Check `<vault_path>/sessions/` for notes matching the domain or topic with frontmatter `status: in_progress` or `status: paused`.
* If an unfinished session exists:
  - Ask the learner via `ask_question` (Preference Mode) whether to resume the previous session or begin a fresh one.
* If starting fresh:
  - Initialize the session note via the graph CLI:
    ```bash
    python3 scripts/graph.py new-session --topic "<topic>" [--domain "<domain>"]
    ```
  - This creates `<vault_path>/sessions/YYYY-MM-DD-<topic-slug>.md` with `status: in_progress` and the standard session template.

#### Step 3: Pedagogical Delegation to `teach` Skill
* Hand off execution directly to `.agents/skills/teach/SKILL.md`, advancing through the 5-phase lifecycle:
  1. **Phase 0 (Resume & Recall):** Inner Fringe prerequisite verification (1 deep conceptual question per direct parent node, branching detour if shaky).
  2. **Phase 1 (Adaptive Probe):** Calibrate knowledge boundary (cold start binary search or warm start goal probe).
  3. **Phase 2 (Plan & Orient):** Verify facts, render 2–3 step DAG in session note and chat, immediately proceed to Step 1 without blocking wait.
  4. **Phase 3 (Teach Loop):** One reasoning step at a time (Motivation $\to$ Solution $\to$ Distinction), Live Mirroring to Obsidian, Metronome Quiz (`ask_question`), anti-guessing remediation, incremental crystallization into `knowledge/<domain>/<slug>.md`, and 1st-order FIRe on parents.
  5. **Phase 4 (Auto-Complete & Sync):** Atomically update session note frontmatter to `status: completed`, run `python3 scripts/graph.py sync --domain <domain>`, and offer optional 1-sentence reflection.

---

### 3.2 `/refresh [domain]`

Launches a voluntary, high-efficiency 5-minute active recall workout on 3–5 high-priority cards using topological Hub Priority and FSRS forgetting curve mechanics.

#### Philosophy: Freedom from Review Hell
Traditional spaced repetition systems (Anki, SuperMemo) induce "Review Hell"—a paralyzing backlog of dozens or hundreds of cards that accumulates during any life hiatus, leading to guilt and abandonment. Antigravity Tutor eliminates this through:
- **Strict Cap:** At most 3–5 cards per session (~5 minutes total).
- **Voluntary Execution:** Initiated only when the user chooses `/refresh`.
- **Topological Hub Priority:** Focuses on foundational hub nodes whose decay threatens downstream knowledge, rather than leaf trivia.
- **1st-Order FIRe:** Normal `/teach` sessions automatically refresh prerequisite parents, keeping the active frontier fresh without explicit review.

#### Step 1: Queue Selection via Graph Engine
Run the refresh selector:
```bash
python3 scripts/graph.py refresh [--domain <domain>]
```
The script evaluates:
* Days elapsed since last review: $\Delta t = \text{today} - \text{last\_tested}$.
* Memory retention estimate:
  $$R = 2^{-\frac{\Delta t}{I}}$$
  where $I$ is `interval_days`.
* Prioritization tiers:
  1. **Tier 1 (Sweet Spot):** $0.4 \le R \le 0.6$ (optimal active recall window). Ranked by Hub Score (number of incoming dependencies), then closeness to $R = 0.5$.
  2. **Tier 2 (Decayed):** $R < 0.4$ (overdue cards). Ranked by Hub Score, then lowest retention.
  3. **Tier 3 (Reinforcement):** $R > 0.6$ (proactive maintenance). Ranked by Hub Score.
* Capped strictly at 3–5 cards.

#### Step 2: Amnesia Protocol Check
* Check CLI output for `[AMNESIA PROTOCOL ALERT]`.
* If the learner has been away for $> 30$ days:
  - **No Guilt or Shame:** Welcome the learner back warmly.
  - **Gentle Runway:** Do NOT hit the learner immediately with hyper-specific technical questions.
  - **Macro Reactivation:** Ask 1–2 high-level, big-picture questions to reactivate high-level mental models:
    * *Example:* *"Welcome back! Before we touch specific mechanisms, let's zoom out: what was the core tension between CPU threads and asynchronous event loops?"*
  - Once the mental model is reactivated, transition smoothly into the selected card queue.

#### Step 3: Active Recall Challenge Loop (1 Question per Card)
For each of the 3–5 selected cards:
1. **Pose 1 Sharp Conceptual Challenge:**
   - Test the **declarative thesis** in the card's title or the core causal mechanism in the note body.
   - **Never ask superficial trivia** ("What RFC defines TCP?", "What year was Go released?").
   - **Ask structural, causal questions:**
     * *"Why does Go use an M:N user-space scheduler instead of allocating a 1:1 OS kernel thread for each goroutine?"*
     * *"Why does a 2-way handshake fail to reliably establish a network connection over an unreliable medium?"*
   - Render the challenge via `ask_question` in Quiz Mode (3–4 plausible options + `"I don't know"` as the final option).
2. **Evaluate & Socrates Grading:**
   - **If Answer is Correct (`solid`):**
     * Brief confirmation of the core principle (1–2 sentences).
     * Advance to the next card immediately.
   - **If Answer is Incorrect or `"I don't know"` (`shaky`):**
     * Provide a concise, intuitive remediation (2–3 sentences, a physical analogy or core contrast; no long lecture).
     * Focus on the generative insight so the concept clicks again.
3. **Update Card State via CLI:**
   Execute the update command:
   ```bash
   python3 scripts/graph.py update-card --slug <slug> --result <solid|shaky>
   ```
   * What the CLI automatically performs:
     - Sets `last_tested: <today>`.
     - If `solid`: advances interval along the progression ($3 \to 7 \to 16 \to 35 \to 90$ days, or $I_{\text{new}} = \text{round}(I \times 2.2)$).
     - If `shaky`: sets status to `shaky` and resets interval to $I = 1$ day.
     - **Practical 1st-Order FIRe:** Automatically updates `last_tested: <today>` on all immediate parents in `depends_on`.

#### Step 4: Workout Summary & Close
Conclude the 5-minute workout with an encouraging, concise summary:
* Total cards reviewed (e.g., *"Workout complete: 4 cards refreshed (3 Solid, 1 Shaky restored)."*).
* Zero backlog guilt: explicitly confirm the graph is synchronized and healthy.
* Suggest next action (e.g., return to `/teach` or wrap up for the day).

---

### 3.3 `/status`

Displays a comprehensive, motivating snapshot of the knowledge vault, the active learning horizon, and retention health.

#### Step 1: Execute Graph Status
Run the status command:
```bash
python3 scripts/graph.py status
```

#### Step 2: Render Structured Status Report
Format the output into an elegant, user-friendly markdown report in the chat:

1. **Vault Overview:**
   - Total crystallized concept cards across all domains.
   - Distribution of statuses: **Solid** vs. **Shaky**.
2. **Domain-by-Domain Breakdown:**
   - **Crystallized Knowledge:** Count of mastered cards.
   - **Active Frontier (Outer Fringe / Ready):** Topics whose prerequisites are 100% satisfied and ready to be studied immediately.
   - **Next Horizon (Locked):** Upcoming topics waiting on prerequisites.
   - **Retention Health:** Average retention estimate ($R$), count of cards in optimal recall window ($0.4 \le R \le 0.6$), and count of overdue cards ($R < 0.4$).
3. **Hiatus / Amnesia Monitor:**
   - Displays max inactive days across the vault.
   - If $>30$ days, displays a gentle notice recommending a quick warm-up workout.
4. **Recommended Next Actions (Proactive Mentorship):**
   - If Ready topics exist on the frontier:
     * Recommend `/teach <ready_topic>`.
   - If retention health shows cards in the optimal recall window or overdue:
     * Recommend `/refresh [domain]` for a quick 5-minute tune-up.
   - If vault is completely fresh:
     * Welcome the user and invite them to start their first topic with `/teach <topic>`.

---

## 4. Dynamic Language Mirroring Protocol

To ensure natural cognitive resonance, **Antigravity Tutor** adheres strictly to the Dynamic Language Mirroring protocol:

1. **Repository & Architecture Standard (English):**
   - All code, scripts (`graph.py`), skill definitions (`SKILL.md`), workspace rules (`GEMINI.md`), git commits, and docstrings must be written strictly in **English**.
2. **User Interaction & Obsidian Notes (Dynamic Mirroring):**
   - The user interface dynamically mirrors the language of the user's input:
     * If the user interacts in **Russian**, all mentoring dialogue, explanations, Socratic probe questions, options in `ask_question`, workout summaries, status reports, and generated Obsidian files (both in `sessions/` and `knowledge/`) must be authored in **Russian**.
     * If the user interacts in **English**, conduct all sessions, write all notes, and render all quizzes in **English**.
     * If the user switches language, adapt smoothly to the current language.

---

## 5. Declarative Antigravity Tool Integration

The `learn` skill interacts with the Antigravity runtime through clean declarative operations:

| Capability | Declarative Pattern | Description |
| :--- | :--- | :--- |
| **CLI Execution** | Run command | Executes `python3 scripts/graph.py <cmd>` (`new-session`, `refresh`, `status`, `update-card`, `sync`). |
| **Interactive Modals** | Modal selection | Calls `ask_question` in Quiz Mode (3–4 choices + "I don't know") or Preference Mode. |
| **Session Journaling** | Semantic note append | Appends explanation quanta, KaTeX formulas, and callouts to `<vault_path>/sessions/`. |
| **Concept Crystallization** | Semantic card write | Saves crystallized concept notes to `<vault_path>/knowledge/<domain>/<slug>.md`. |
| **Diagrams** | Native Mermaid | Renders structural DAGs, roadmaps, and horizon blocks using pure text labels without `[[...]]`. |
| **Formulas** | Native KaTeX | Typesets mathematical formulas using inline `$...$` and display `$$...$$`. |

---

## 6. Edge Cases & Resilience Protocols

1. **Empty Vault:**
   - When `/status` or `/refresh` is invoked on an empty vault:
   - Provide a clear, friendly explanation that no concept cards have been crystallized yet.
   - Offer 2–3 suggested topics to explore via `/teach <topic>`.
2. **Missing Prerequisite / Broken Dependency:**
   - If a card references a `depends_on` node that does not exist on disk, treat it defensively as a virtual node `(Locked)` without crashing.
   - The CLI outputs a non-fatal warning to stderr and continues graph processing.
3. **Graph Cycles:**
   - If a dependency cycle is introduced, `scripts/graph.py sync` detects it via Tarjan's algorithm, emits the exact cycle path (`A -> B -> A`) to stderr, and halts before corrupting `_index.md`.
   - The mentor immediately alerts the user, analyzes the circularity, and resolves the prerequisite loop.
4. **Interrupted `/refresh` Workout:**
   - Because each card is updated atomically via `graph.py update-card` as soon as it is answered, interrupting a refresh session leaves no corrupted state or uncommitted progress. Any answered cards remain saved.
