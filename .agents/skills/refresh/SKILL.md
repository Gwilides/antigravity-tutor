---
name: refresh
description: >-
  Voluntary, high-efficiency 5-minute active recall workout for Antigravity Tutor.
  Selects 3–5 high-priority concept cards using topological Hub Priority and the exponential
  forgetting curve (R = 2^(-Δt/I)), handles long hiatuses via the Amnesia Protocol,
  and updates card retention intervals without Review Hell.
---

# Active Recall Workout Skill (`refresh`)

This skill defines the operational and pedagogical protocol for **Antigravity Tutor's active recall workout engine**. It governs how the mentor executes voluntary, stress-free micro-reviews triggered by the user slash command `/refresh [domain]`.

The goal of `/refresh` is to maintain the long-term structural integrity of crystallized knowledge in the learner's Obsidian Vault without ever inducing the cognitive dread, backlog anxiety, or abandonment associated with traditional Spaced Repetition Systems (SRS).

---

## 1. Cognitive Architecture & Anti-"Review Hell" Philosophy

### The Trap of Traditional SRS (Review Hell)
Traditional flashcard tools (Anki, SuperMemo) suffer from a fatal flaw: **backlog accumulation**. Missing a few days piles up dozens or hundreds of overdue reviews. The learner returns to a wall of shame, experiences cognitive overload and guilt, and eventually abandons the system entirely.

```
Traditional SRS (Linear Backlog Dread)
[ 100+ overdue cards ] ──► Cognitive Guilt ──► Burnout ──► Total Abandonment

Antigravity Tutor (Bounded Topological Workout)
[ Voluntary /refresh ] ──► Cap: 3–5 Hub Cards ──► 5-Minute Sprint ──► Energized Mastery
```

### The Antigravity Tutor Alternative: Topological Micro-Workouts
1. **Strict Review Cap (3–5 Cards Max):** A refresh workout tests a maximum of **3 to 5 cards**, regardless of how many concepts reside in the vault. Zero backlogs. Zero guilt.
2. **5-Minute Hard Time Budget:** The entire interaction is calibrated to complete in under 5 minutes.
3. **Pure Active Retrieval:** Every tested concept requires active causal derivation, not passive recognition or rote term matching.
4. **Voluntary Execution:** Reviews are initiated by the learner on demand (`/refresh [domain]` or global `/refresh`), or suggested as a light optional warmup before a `/teach` session.

---

## 2. Mathematical Mechanics: Forgetting Curve & Hub Priority

Selection of the 3–5 cards is computed automatically by `scripts/graph.py refresh` using two cognitive parameters:

### 2.1 The Exponential Forgetting Curve
Retention probability $R$ is modeled as a simple exponential decay:

$$R = 2^{-\frac{\Delta t}{I}}$$

Where:
* $\Delta t$: Elapsed calendar days since `last_tested` ($t_{\text{today}} - t_{\text{last\_tested}}$).
* $I$: Current stability interval in days (`interval_days`), representing the half-life of reliable recall.
* $R$: Estimated probability of successful unassisted retrieval ($0.0 \le R \le 1.0$).

### 2.2 The "Desirable Difficulty" Sweet Spot Window ($0.4 \le R \le 0.6$)
Borrowing from Bjork's principle of **Desirable Difficulty**, active recall yields the highest synaptic consolidation when retrieval requires substantial cognitive effort but does not fail completely:

```
Retention (R)    1.0 ────────────── 0.6 ────────────── 0.4 ────────────── 0.0
Zone:            [ Too Easy / Fresh ]   [ Optimal Challenge ]   [ Overdue / Decayed ]
Action:          Low consolidation     Maximum consolidation   High risk of failure
Priority:        Tier 3 (Maintenance)   Tier 1 (Target Window)  Tier 2 (Rescue)
```

* **Target Window ($0.4 \le R \le 0.6$):** The memory trace has begun to fade, forcing the brain to reconstruct the derivation. This produces the highest durability gain per minute spent.
* **Overdue Zone ($R < 0.4$):** Decayed memory traces requiring urgent remediation before they bottom out.
* **Fresh Zone ($R > 0.6$):** Well-consolidated concepts; testing these yields diminishing returns.

### 2.3 Topological Hub Priority (Graph In-Degree Weighting)
In a Knowledge Space DAG, concepts are not isolated facts—they are interdependent nodes. Forgetting a leaf concept is a minor loss; forgetting an architectural hub breaks all downstream understanding.

The **Hub Score** $H(c)$ of a concept card $c$ is the number of other concept cards in the vault that directly depend on it:

$$H(c) = |\{ v \in V \mid c \in \text{depends\_on}(v) \}|$$

### Card Selection Priority Ranking
When `scripts/graph.py refresh` gathers candidates, it partitions cards into three tiers and ranks them deterministically:
1. **Tier 1 (Sweet Spot: $0.4 \le R \le 0.6$):** Sorted by highest Hub Score $H(c)$ descending, then by proximity to the center of the window $|R - 0.5|$ ascending.
2. **Tier 2 (Overdue: $R < 0.4$):** Sorted by highest Hub Score $H(c)$ descending, then by lowest retention $R$ ascending.
3. **Tier 3 (Fresh: $R > 0.6$):** Sorted by highest Hub Score $H(c)$ descending, then by lowest retention $R$ ascending.

The final queue selects the top **3 to 5 cards** across these tiers.

---

## 3. The Amnesia Protocol (Long Hiatus Management)

When a learner returns after an extended break ($\max \Delta t > 30$ days), jumping directly into granular, complex quizzes triggers immediate failure, frustration, and cognitive paralysis. The mental models are not dead, but their associative schemas are dormant.

### Trigger Condition
* `max_delta_t > 30` days across the selected cards or target domain.
* Flagged automatically by `scripts/graph.py refresh` with:
  `⚠️ [AMNESIA PROTOCOL ALERT] Long hiatus detected: max inactive interval is X days (> 30 days).`

### Protocol Execution
1. **Do NOT open with a detailed technical quiz.**
2. **Reactivate the Schema (1–2 Macro Questions):**
   * Before presenting Card 1, ask **1–2 gentle, high-level bird's-eye questions** to reactivate the overarching mental model and big picture.
   * Focus on architectural motivation, core trade-offs, or the fundamental problem the domain solves.
   * Keep the tone encouraging, warm, and low-pressure.
3. **Transition to Workout:**
   * Once the high-level schema is warm and unblocked, seamlessly transition into the 3–5 card testing sequence.

---

## 4. Card-by-Card Testing Protocol

For each card in the queue (maximum 5), execute the following rhythm:

```
[ Step 1: Sharp Conceptual Challenge via ask_question ]
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   [ Solid Answer ]              [ Shaky / Don't Know ]
        │                                 │
   • Brief Validation                • 1-Paragraph Intuitive Refresher
   • Advance Stepwise Interval       • Reset Interval to 1 Day
   • graph.py update-card solid      • graph.py update-card shaky
   • 1st-Order FIRe on Parents       • Mark status: shaky
        │                                 │
        └────────────────┬────────────────┘
                         ▼
             [ Next Card or Conclusion ]
```

### 4.1 Sharp Conceptual Challenge via `ask_question`
* Pose **exactly 1 sharp conceptual challenge** per card.
* **Content:** Target the generating principle, causal mechanism, or boundary condition. **Never ask for dictionary definitions, syntax trivia, or arbitrary names.**
* **Format:** Use `ask_question` in Quiz Mode:
  - 3–4 parallel, plausible options of similar length and grammatical shape.
  - Plausible distractors based on common cognitive traps.
  - Final option: strictly `"I don't know"`.
  - Never add `(Recommended)` to quiz options.
  - Order options neutrally.

### 4.2 Socratic Grading & Interval Adjustment

#### Case A: Solid Comprehension (Correct with Derivation)
1. **Brief Validation:** Provide a 1–2 sentence confirmation reinforcing *why* the answer is structurally sound.
2. **Stepwise Interval Progression:** Advance the card's `interval_days` along the standardized sequence:
   $$3 \to 7 \to 16 \to 35 \to 90 \text{ days}$$
   If current interval is already $\ge 90$ days:
   $$I_{\text{new}} = \text{round}(I_{\text{old}} \times 2.2)$$
3. **Persist to Obsidian Vault:**
   Execute the graph engine helper:
   ```bash
   python3 scripts/graph.py update-card --slug <slug> [--domain <domain>] --result solid
   ```
4. **Practical 1st-Order FIRe (Foundational Interval Renewal):**
   * Testing concept $B$ directly tests the stability of its prerequisites $A \in \text{depends\_on}(B)$.
   * `scripts/graph.py update-card` automatically updates `last_tested: <today>` on all immediate parents in the vault, keeping foundational hubs fresh without redundant testing.

#### Case B: Shaky Comprehension (Incorrect / Hesitation / "I don't know")
1. **CRITICAL PEDAGOGICAL RULE:** **Do NOT deliver a full lecture.**
   * This is a 5-minute active recall workout, not a Phase 3 `/teach` deep dive.
   * Provide a **concise, intuitive refresher** (1 crisp paragraph): a concrete analogy, a physical metaphor, or a 1-sentence reminder of the core tension.
2. **Interval Reset:** Reset `interval_days` to **1 day** ($I_{\text{new}} = 1$) and mark `status: shaky`.
3. **Persist to Obsidian Vault:**
   Execute the graph engine helper:
   ```bash
   python3 scripts/graph.py update-card --slug <slug> [--domain <domain>] --result shaky
   ```
4. If the learner wants a complete re-derivation from scratch, note that they can run `/teach <topic>` later. Keep the current workout moving!

---

## 5. Session Conclusion & Summary

Upon completing the 3–5 cards:
1. **Present a Crisp Summary Table:**
   Render a clean Markdown table summarizing the workout:

   | Concept | Result | Prior Interval | New Interval | Next Check-in |
   | :--- | :---: | :---: | :---: | :--- |
   | Goroutines vs OS Threads | Solid | 7d | 16d | ~2 weeks |
   | Channel Synchronization | Solid | 3d | 7d | ~1 week |
   | Work-Stealing Runtime | Shaky | 16d | 1d | Tomorrow |

2. **Graph Synchronization:**
   Run graph synchronization to ensure horizon indexes reflect the updated statuses:
   ```bash
   python3 scripts/graph.py sync [--domain <domain>]
   ```
3. **Encouraging Wrap-Up:** Close with an encouraging 1-sentence note. Total time spent: under 5 minutes.

---

## 6. Dynamic Language Mirroring

* **Repository Artifacts:** Skill files, workspace rules, Python scripts, and internal instructions are authored strictly in **English**.
* **Learner Communication:** All interactive prompts, questions in `ask_question`, feedback explanations, and summaries must **dynamically mirror the language the user speaks**.
  * If the user interacts in Russian, conduct the refresh workout, ask quizzes, and format summaries in Russian.
  * If the user interacts in English, conduct the entire session in English.

---

## 7. Complete Execution Walkthrough

### Example Interaction

```text
User: /refresh go-concurrency

Mentor (Internal):
1. Runs: python3 scripts/graph.py refresh --domain languages/go
2. Output parses 3 cards:
   - goroutine-stack-growth (R=0.48, Hub=2, dt=15, I=16)
   - channels-unbuffered-rendezvous (R=0.52, Hub=1, dt=7, I=7)
   - select-fairness-pseudo-random (R=0.38, Hub=0, dt=12, I=7)
3. max_delta_t = 15 <= 30 -> Amnesia Protocol not triggered.
4. Announces: "Welcome to your 5-minute active recall workout! Today we have 3 high-leverage concepts to reinforce."

Card 1: goroutine-stack-growth
Mentor calls ask_question:
"When a Go goroutine exhausts its current stack frame during deep recursion, how does the runtime allocate more memory without causing memory fragmentation?"
Options:
- [A] It links a new independent 8KB memory chunk in a contiguous linked list of stack segments.
- [B] It allocates a new contiguous buffer twice the size, copies existing stack frames, and adjusts internal pointers.
- [C] It triggers an OS page fault that prompts the kernel to map virtual memory pages on demand.
- [D] I don't know.

User selects [B].
Mentor:
"Spot on. Split stacks caused hot-split thrashing, so Go moved to contiguous copy-on-grow stacks.
Advancing interval: 16d -> 35d."
Runs: python3 scripts/graph.py update-card --slug goroutine-stack-growth --domain languages/go --result solid

[Card 2 and Card 3 follow the same rapid tempo]

Session Wrap-Up:
Mentor prints concise summary table, runs python3 scripts/graph.py sync --domain languages/go, and concludes.
Workout duration: 3 minutes 40 seconds.
```
