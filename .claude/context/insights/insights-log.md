# Jarvis Insights Log

Captured automatically by insight-capture.js hook.
Processed by /reflect Phase 5 for Graphiti ingestion.

---

### 2026-08-24 [a10a4549d14f]

**The restart script has no credential passthrough at all.** It respawns the window reusing the retained `pane_start_command`, so the new pane inherits the tmux *server's* environment — and this server was started 15 Aug, well before the credential exports existed. Restarting the lanes as-is would bounce all six and leave Graphiti exactly as broken, which is precisely the silent-degradation shape I've been fixing all day.

It also only knows four lanes (`jaques|genie|dev|w0`) — it has no mapping for `urist` or `protos`.

### 2026-08-24 [c6bb0dd592de]

- **The MLX-Embed alert was a startup race, not a fault.** The watcher's MAINTAIN health probe fired at `17:09:45`; the MLX server logged "loaded successfully" at `17:09:49` and has served 200s since. The probe raced the very session start that spawned it — a health check with no startup grace window will always libel a service that boots alongside it.
- **A refused connection and a dead service are indistinguishable to a single-sample probe.** That's the [[reference_dead_metric_and_blind_gold]] shape: the metric can't tell "not yet" from "never." A second sample 30s later splits them for free.

### 2026-08-25 [68d919c3cec8]

- **`--strict-mcp-config` replaces the entire config, not just the project layer.** It's there for a good reason on Genie — it's what binds `GRAPHITI_GROUP_ID` to `genie-core` instead of the root file's hardcoded `jarvis-core`. But the side effect is that the three strict lanes silently lose Gmail, Calendar, PubMed and Mermaid. Urist and Jacques inherit that cost without needing the benefit.
- **`claude-in-chrome` survives `--strict-mcp-config`** — it's harness-injected, not config-driven. That's why the strict lanes still had chrome tools throughout the outage, and it confirms the earlier finding that the blocker was never per-lane MCP config.

### 2026-08-25 [7de2f1f32bac]

- This inverts where variation lives: from **four files that must be kept in sync** to **one file plus per-lane env**. Drift becomes structurally impossible rather than merely discouraged — which matters, because the drift already happened and went unnoticed for months.
- Note the deliberate asymmetry with secrets: line 1230 warns *never* to write `${VAR:-<password>}`, because a default would re-embed the secret and make a failed export invisible. A group ID is not a secret and `jarvis-core` is the correct fallback, so defaults are right here and wrong there.

### 2026-08-25 [6226d19a7ac3]

- `aion-lane-restart.sh` carries a **duplicate copy** of the launch command rather than deriving it from `launch-aion.sh`. That's the exact drift generator I just eliminated in the MCP configs, reappearing one layer up: two places that must agree, with nothing enforcing it.

### 2026-08-25 [f695ccb497e3]

- **The checkpoint and the scratchpad disagreed, and the scratchpad won.** `dev.compressed.md` is an LLM re-summary (qwen3:8b) of a session; it listed brotli, graphiti group-ids, MCP levelling and read-any as `TODO`. All four had shipped. The scratchpad is hand-written by the lane that did the work — lossless where the checkpoint is lossy. When they conflict, probe, then believe the primary.
- **`/health` returning 200 proves the port answers, not that new code is behind it.** Verifying deployment needs a *discriminating* probe — one whose output differs between old and new build. Here that's `proxy.DECODABLE_ENCODINGS`, which only exists post-fix.

### 2026-08-25 [6bca70320815]

- **No divergence — `Alfred-Dev` is a symlink to `Project_Aion/alfred`.** `lsof` reports the *resolved* path while `pane_start_command` holds the *symlink* path, so the same directory looked like two. The launcher uses the symlink deliberately: entering via the symlink keeps Claude Code from seeing the monorepo's `.git`.
- This also corrects my own §0.-29/§0.-30 notes, which described Alfred-Dev as a separate non-git location. It's the same directory reached by another name.

### 2026-08-25 [db2333ba99c2]

Default `SPAN_MODE = "tokens"` builds each row's span from the **union of its token extents**, then R3 promotes the row to a body row if that span reaches `0.75 × measure` and is flush at an edge — and R4 then labels every token in a body row `MT`. The comment at line 444 records this exact break: *"leaf 406's headline row was promoted to a body row by a 3-glyph UNREAD speck sitting at the left margin… and the running head was then labelled MainText."*

The span clause was added to stop specks doing it. On leaf 410 the intruder at x=0.19 is **not** a speck — it's a real line of type that far-chaining correctly recovered — so `MIN_GLYPHS` doesn't filter it, the union span reaches the left edge, and the head row is promoted. My row fix made the classifier's weakest assumption load-bearing.

And the remedy is already written, sitting at default-off: `SPAN_MODE = "segment"` — *"A justified body line is CONTINUOUS across the measure; a headline band is SPARSE ISLANDS. Extent cannot tell them apart… Computed on GLYPH BOXES, so no splitter can move it."* Leaf 410's row 0 is three sparse islands, so its longest continuous run never reaches 0.75 × measure and the row is never promoted.

### 2026-08-25 [c6faf06ae811]

**S-A failed hard:** segment mode collapses the *control's* MainText from 0.8375 (67/80) to **0.7000 (56/80)** — eleven main-text entries lost in production. It buys MN with MT. Note it damages the control far more than the candidate (whose MT only slips 0.8375→0.8289), because with greedy rows the longest continuous run often fails R3's span test, so genuine body rows stop qualifying and their tokens fall through to MN/RH.

**S-D also failed, and that's the more useful finding:** 419.0.0 is *still* mislabelled. So the two lost margin notes do **not** share a cause, and I had merged them wrongly. Leaf 410 is a **labelling** failure — the row gained a token and R3 promoted it. Leaf 419 is a **clustering** failure — its row 0 holds entirely different tokens and the leaf drops 24 → 21 rows. Segment mode addresses only the first.

### 2026-08-25 [10f83a886ebd]

The pattern repeats down the page: control row `212.0 n=42 x 0.120–0.925` becomes **two** candidate rows — `211.0 n=9 x 0.813–0.891` and `214.5 n=34 x 0.120–0.904`. Those small right-hand fragments at x≈0.81–0.94 are the **margin-note column**. The seeded row model is *separating* the marginal grid from the body line, which is physically more correct — they genuinely have different baselines. At row 0 the same thing happens on the left: the glyph at x=0.026 moves from the y=128 row to a new y=151 row, 0.59 pitches down, taking the margin note with it.

So the candidate isn't losing 419's margin note through error. It's putting it on its own baseline, and `region_head` then relabels because **R3/R4 promote and label whole ROWS**, while the module's own founding observation is that *"a row is not homogeneous in REGION (which is why labels are per token)."* R3/R4 never got that memo.

### 2026-08-25 [b78e4fdce57d]

`R4_PER_SEGMENT=True` produces **bit-identical numbers to False in every arm** — RH, MN, MT, pairs, sinks, all four figures unchanged. The flag is **inert**. That is a criterion that cannot fail: anyone who "tested" R2.2f by flipping it and observing no regression would have concluded it was safe, when in fact it does nothing. This project has a name for the shape — a rule nothing reads — and my own memory carries the rule for it: *when a null appears, validate the mechanism before believing the verdict.*

### 2026-08-25 [902f09bfa350]

`_in_body_seg` returns `True` when `t["row"] not in body_segs`. And `body_segs[j]` is only populated when some segment of the row qualifies. For exactly the rows in question — a head row of sparse islands wrongly promoted by its token-union span — **no** segment qualifies, so the row lands in `fallback_rows`, `body_segs` never gets an entry, and every token falls back to being labelled body. The per-segment rule is bypassed precisely where it was needed.

The fallback is the defect. If a row was promoted by union span but **no continuous segment reaches the measure**, that promotion was an artefact of summing across gaps — it is sparse islands, not a justified line, and the row should be **demoted**, not labelled body anyway. `fallback_rows` is already computed and counted "so the reach stays knowable" — the module measures the case and then ignores what it means. Instance #16.

### 2026-08-25 [4c602c11715e]

Lines 178–181 say the fallback is **deliberate**: *"IT MAY ONLY DEMOTE. A row where NO segment qualifies keeps today's behaviour… stripping MainText from such a row would be this rule answering a question it was not asked."* So demotion was considered and refused on scope grounds. I'm not correcting an oversight; I'd be reversing a reasoned decision, which needs its own pre-registered candidate and an explicit argument — not a quiet flip.

The argument now exists: when that comment was written there was no evidence the union-span promotion was itself wrong. Leaf 410 supplies it. But line 169 carries something bigger: *"THE GOLD'S MN 0.8947 WAS RESTING ON THAT: two errors cancelled, and the first genuine repair exposed the second."* **The control's MN 0.8947 is itself the product of two cancelling errors.** My S-A and S-B bars are both anchored to that number.

### 2026-08-25 [95e85c5a320d]

Every intervention that improves MN costs MT the same way in the control: MT falls 67/80 → **55/80** (demotion) or **56/80** (segment span), while MN rises 17/19 → 18/19. Three different levers, one signature. That says the control's MT 0.8375 **depends on rows being promoted by extent summed across gaps** — and that a large number of *genuine* body rows fail the continuous-segment test.

Which indicts the shared primitive. `region_segments` cuts a row wherever a gap exceeds the line pitch, on the stated rule that *"a gap wider than the line pitch is a run to another region, not a word space."* In justified early-modern setting, word spaces are stretched to fill the measure and routinely **do** exceed the pitch. If so, the primitive is shredding real body lines, and both candidates inherit that error.

### 2026-08-25 [2fa1375d6346]

Of 301 rows whose token union spans ≥0.75 of the measure — i.e. genuine body lines — **102 (34%) have no continuous segment reaching 0.75**. Only 49% are a single segment; the median row is cut into two. Just 2.3% of intra-row gaps exceed one pitch, but those 261 cuts are enough to shred a third of the body.

So the refutation of `SPAN_MODE="segment"`, of `R4_PER_SEGMENT`, and of R2.2n is **one refutation, not three**. All rest on `region_segments`, whose cut rule cannot distinguish a stretched word space in justified setting from a genuine run out to the margin. Adding a fourth rule on top would inherit the same error.

### 2026-08-25 [5d09ef543385]

The script contains a guard that fired **against** the more flattering number. Folding same-label seams into the must-not-cut population is legitimate only if no seam spans the text block — so the script checks at run time whether any seam reaches region-gap width. Seven of 39 do, so it refused the fold and reported the stricter accounting. A check that can only ever confirm the answer you want isn't a check; this one had a live way to say no, and did.

### 2026-08-25 [6585f128e211]

- **"All MCP servers disconnected"** at session start looked like the silent zero-MCP failure from §0.-35. It was startup latency — servers reconnect in waves. The real check is whether they resolve *eventually*, not whether they're present in the first second.
- **My warning count of "1"** was my own `grep` command echoed into the pane, matching its own search string. Same self-match trap as polling for a token your input contains. The actual count is zero.

### 2026-08-25 [625cf431ced4]

Genie, Jaques and Urist all get `GRAPHITI_GROUP_ID` exported by the launcher. **Protos does not** — its launch line exports only four variables. So a `${GRAPHITI_GROUP_ID:-protos-core}` default would normally fire correctly *and* let a chain fork override it, which is the lever for the §0.-30 open question about N chains sharing one namespace.

But that only holds if the variable is genuinely unset. If it leaks in from the tmux server env as `jarvis-core`, Protos would silently write into W0's graph — the precise pollution §0.-30 warned about.

### 2026-08-25 [99b96e5e37a4]

Verified by launch, not by parse: `your_group_id` resolved to **`protos-core`** — so the `${GRAPHITI_GROUP_ID:-protos-core}` default fired correctly and did *not* fall through to `jarvis-core`. Graphiti also authenticated and read the graph, which proves `${NEO4J_PASSWORD}` expanded too. And `mcp-hot-reload` itself is proven working, since graphiti resolved *through* the wrapper.

### 2026-08-25 [d77564d76bf7]

**The obvious fix — copy root's config — would have been a silent no-op.** `mcp-hot-reload` resolves watch globs against `process.cwd()` (confirmed in its source: `path.join(process.cwd(), …)`). Protos' cwd is `alfred/`, not the repo root, so root's relative `infrastructure/rag-service/…` would resolve to `alfred/infrastructure/…` — a path that doesn't exist. Hot reload would watch *nothing* while looking perfectly configured.

That's worse than having no wrapper: a broken feature that reports as present. The other five lanes' relative paths are fine precisely because their cwd *is* the repo root. A path is only portable relative to a cwd you've actually verified.

### 2026-08-25 [e201ecb7dbc3]

`MN 0/19` reads like blindness and isn't. The MarginNote entries bind to **tight** boxes — median 0.0039 of page area, not the half-page `Text` block — so Surya **localises the notes as distinct objects** and simply has no *name* for them. Its vocabulary is modern-document: Caption, Footnote, PageHeader, Table, Code, ChemicalBlock. No marginalia class. That makes the repair a **class-inventory fine-tune of a working detector**, not a detector built from scratch — materially cheaper than R14.1 assumed. It also confirms the hybrid §3.2 item 5 specifies: the hand-built geometric component is currently **the only thing in the project that can name a marginal note**.

### 2026-08-26 [06bee4611a3e]

W11 reported "1 permission warning" and it was again my *own grep command* echoed into the pane, matching its own search string. That's twice in two sessions. The durable fix is to search for the warning's distinctive prefix (`Permission allow rule (`) rather than its human-readable tail, so the query can't match its own text — same class as never polling for a token your input contains.

### 2026-08-26 [54166f450ff7]

**Blocking discards the reason's guarantee, so I use two paths.** A blocked `UserPromptSubmit` definitely stops the payload reaching the model, but whether its `reason` string is *injected into my context* (vs. shown only to you) isn't documented. So the hook does both: it emits `reason`/`systemMessage` on the block, **and** drops a `.pending.json` marker. On your very next prompt — which is small — the hook injects the invitation via `additionalContext`, a field the docs explicitly define as "Text injected into model context." The guaranteed path carries the payload even if the best-effort one is silent.

### 2026-08-27 [811bf5fa1ba8]

**The generator edit is the one that actually matters.** `alfred/.claude/settings.json` is headed *"generated by profile-loader.js"* — and that script does `fs.writeFileSync(SETTINGS_PATH, ...)` at `:707` from a literal built at `:413`. It never reads the existing file. A hand-added `statusLine` would have been silently wiped the next time anyone ran the profile loader, and the drift would have reappeared with no obvious cause. I verified via `--dry-run` that the generator now emits it. Fixing the output without fixing the generator would have been a fix with an expiry date.

**Absolute paths, not `$CLAUDE_PROJECT_DIR`.** DwarfCron's own `_comment` already documents why: that variable resolves to the satellite dir, which has no `.claude/scripts/`, so a relative path renders nothing — silently. I matched the convention the file already argued for.

**The user-level fallback closes the loop.** Pointing `~/.claude/settings.json` at v9 too means any *future* lane inherits the standard rather than the stale Feb script. Without it, this exact drift recurs the next time an Archon is added.

### 2026-08-27 [7418eef9c1c0]

**The dangerous references aren't the ones in config.** I checked `settings.json` everywhere, LaunchAgents, and crontab — all clean, which is what made retirement safe. But the one that mattered was a *string literal inside an error message*, which no config-oriented search would surface. Grepping `*.sh`/`*.js` for the filename, not just the config files, is what found it. Retiring a script means retiring every place that names it, including the places that only name it when something else has already gone wrong.

**`git mv` matters more than it looks.** Staging showed `R100` — a 100%-similarity rename, so `git log --follow` still traces v8's full history. Had I done `rm` + `add`, git would have recorded a delete plus an unrelated new file, and the provenance of the layout that four lanes ran for months would be gone from the log.

### 2026-08-27 [ae78577bf7d4]

**Two "different" remotes were the same repository.** DwarfCron has both `origin` and `cannoncopilot` pointing at `git@github.com:CannonCoPilot/DwarfCron.git`, and `Dev` had no tracking config, so `git push` with no argument would have been ambiguous. Checking `git remote -v` before choosing the target turned what looked like a fork decision into a no-op.

**Project_Aion has a decoy remote.** Alongside `origin` sits `jarvis-legacy` → `CannonCoPilot/Jarvis.git`, the pre-monorepo repository. Pushing `main` there would have dumped the entire Aion monorepo history into the retired Jarvis repo. Naming `origin` explicitly, rather than relying on a default, is what avoided it.

### 2026-08-27 [1fc083df352c]

- **The whole MarginNote problem was a framing error, not a threshold error.** R2.2o.1 proved no gap constant exists because it kept asking *how far is this from the body*. A note is not far from the body — it is **beside** it, and besideness is a fact about a per-page frame. That one reframe took MarginNote 0/19 → 13/19 with no fitted constant deciding anything.
- **A cue that turns on a last pixel is a threshold in disguise.** `y1 <= head_y` failed by 0.0015 of a page and killed 11 of 20 running heads. Judging the box's *mass* is the visual fact; judging its last pixel is a tolerance nobody declared.
- **Abstention with a cause is a debugger.** 3 of 6 residual misses read `cue says MN, but archetype A forbids it` — which localised the next repair to the archetype classifier without any further investigation.

### 2026-08-27 [b83f17313ce0]

- **The misfiling is decided entirely by `SMALL_AREA`, not by anything about the class.** Argument box areas run 0.0443–0.1211 against a 0.05 size prior; every box above it became `MT`, every box below became `CH`. Ten for ten. The agent was never reading the Argument at all — a constant was picking which wrong name it got.
- **That makes the true defect 10/10, not the 4 R14.8 recorded.** GOLD-FOREEDGE's five leaves happened to be the small-box side, so it only ever saw the `CH` half. The `MT` half is the *silent* half — and MainText is containment, so it looks correct in every score.
- **The instrument already existed.** `region_head` has defined `ARGUMENT = "AR"` with a validated fount test since R2.2d, and no rule read it. Third instance of working-code-no-rule-governs.

### 2026-08-27 [28f86548b4f3]

- **The headline ranking was backwards, and now it is measured rather than merely doubted.** `dr_v3_armA` carries the highest validation accuracy on this disk (0.9739) and comes **last** of the three un-vetoed models on a common set (0.8597). `reichenau_dr` — the 0.9396 every document cites — wins one class of seven. The Roadmap warned this *could* be true; R2.1b shows it *is*.
- **The ſ veto did real work, and it disqualified the "honest generalisation" model.** `reichenau_dr_ho` was built specifically to hold pages out — and it modernises the long s (0.8372). Its pooled content of 0.8693 beats `reichenau_dr`'s per-class record in places, which is exactly the trade the two-metric design exists to refuse.

### 2026-08-28 [c38d40202b86]

- **"No angle" is a different failure from "wrong angle."** I checked and the agent has no rotation concept at all — axis-aligned boxes, horizontal head line, vertical measure. The tilt exists (−2.39° to +2.75°) and at 1.6° it drops a full line-height across the page, which is exactly why one horizontal line severs 41 boxes.
- **A quantised estimator reads zero and looks like a clean page.** `slant_mode` is integer-degree glyph slant, and it reports 0.00 on all 20 leaves. Had I trusted it as skew, I'd have concluded the scans were square. The rows say otherwise.
- **The most important finding needed no code — just a grep.** There are zero prompts in the agent path. The gap between what you thought was running and what is running was never going to close by measuring outputs.

### 2026-08-28 [5786f0dbaec8]

**The chart was not merely mislabelled, it was inverted.** Plotting `input + output` while excluding cache reads means the number *falls* as caching improves. A spike is a cache miss, not a big prompt. Measured live: the panel's max was 4,192 tokens while the real maximum prompt in that same window was 360,976. An 86× understatement.

**"Everything up-to-date" is not proof your work is pushed.** It was literally true: local `main` was unchanged. HEAD had moved to another branch underneath me. The push reported success on a ref my commit was never on.

### 2026-08-28 [15ae875d33d0]

- **Building a step is the cheapest way to test the reason you filed it.** I attributed 41 cut boxes to the missing angle. Rotating the frame moved the count the *wrong way* and the correlation came back at +0.051 — the premise was false, and only implementing it revealed that. The rotation is still correct groundwork; the causal story was not.
- **"Exactly unchanged" can be a warning as much as a pass.** GOLD-HEADBAND held at 115/121 through the rotation, but that is because every gold here scores *labels*, and the tilt's real cost is a *boundary* error — a box 17% too tall on leaf 409. The instrument is blind to the axis where the defect lives.
- **A criterion can be circular and still look rigorous.** My clause "the estimated angle should correlate with measured row tilt" could only ever return 1.0, since the estimator *is* the row tilt. Pre-registration doesn't protect you if the criterion tests the instrument against itself.

### 2026-08-28 [1796dfa98c2a]

**The checkpoint lied about whose task this is.** Its "Current Task" read "Rotate the password as requested." The qwen3:8b summarizer flattened my *request to Sir* into an instruction *from* Sir. A compressed checkpoint preserves topic reliably and preserves speaker direction poorly. Acting on it would have meant rotating a live shared credential nobody authorized.

**`git grep` and `/usr/bin/grep` answer different questions, and both were needed.** `git grep` says the tracked tree is clean. `/usr/bin/grep` found five more copies on disk. `git check-ignore` then proved all five are gitignored. Neither tool alone distinguishes "published" from "merely present."

**My first sweep swept the wrong secret.** `grep -A5 -i chronicler` landed in an adjacent block and returned the Neo4j password. The tell was the history hits naming a Neo4j rotation. `credentials.yaml` is multi-document, so anchoring on a nearby word is not anchoring on a key.

### 2026-08-28 [cd0c883f5498]

- **Sweeping the credential *store* is what caught it.** I compared every changed file against all 80 values in `credentials.yaml`, not against strings that "look secret." A regex for high-entropy tokens would have found this one, but the method also covers passwords that happen to look like words.
- **The raw result was 46 hits and 45 were noise** — `localhost`, `chronicler`, `pulse_dev`, base URLs. What separated signal from noise was ranking each match *by its key name in the store*: `database.postgres.password` is a secret, `database.neo4j.host` is not. Reporting 46 leaks would have been crying wolf; reporting zero because "most look benign" would have missed the real one.
- **Checking HEAD before choosing the remedy is what changed the answer.** Had the password existed only in the working tree, redacting would have been sufficient and rotation overkill. It was already committed, which converts this from a tidy-up into a rotation.

### 2026-08-28 [abbc781439f2]

- **The archive file had accepted this credential in writing**, with the rationale *"since the repo is private and this is a local Docker…"*. The premise was false when written. I corrected it in place rather than deleting it, so the reasoning error stays visible — a deleted bad rationale teaches nothing.
- **Ranking matches by key name is what makes the sweep usable.** My first pass returned 46 hits, 45 of them `localhost` / `chronicler` / `pulse_dev` / base URLs. Reporting 46 leaks is crying wolf; dismissing them as mostly benign buries the real one. The store's own key path (`database.postgres.password` vs `database.neo4j.host`) is the discriminator.

### 2026-08-28 [e1c3b75c196f]

- **Of 208 leaves, exactly 6 carry no flag — and all 6 are `OT1-1609-B`**, the witness LECTOR was built on. That's the generalisation result in one line, and it's the strongest argument yet for R14.16: replace the hand-written cascade with a learned classifier.
- **Archetype `A` fires 9 times here.** It has never fired on the 20-leaf window, which is exactly why `forbidden=0` was recorded as *trivially* true. The FORBIDS contract can finally bind.
- Both failure modes trace to one assumption — "the largest box is the body" — that was true on one scan and was never a property of the book.

### 2026-08-29 [af7af02cf0ae]

- **One cause, not fourteen defects.** Whatever falls above `head_y` or below `foot_y` gets renamed, regardless of what it is. Body verses become `SG`. Body continuations become `CH`. Annotation blocks become `MT`, `SG` or `CH` depending purely on where the rule lands.
- **This is the frame-anchor finding, seen from the label side.** `frame()` anchors on the largest box. When that box is not the body, `head_y` and `foot_y` land inside the text, and everything outside them is relabelled by position rather than by kind.

### 2026-08-29 [76c6740c959d]

- **Column loss is not a table problem.** `NT-1582-B_0438` sets a two-column parallel comparison inside the body text, and it is wrapped as one `MT` block. I had scoped `E13` to contents tables. It reaches ordinary pages too, which means a trained model would learn that two columns are one region.
- **The margin is the strong part of this witness.** Across 30 NT leaves, margin notes are almost always correct, including very long ones. Whatever is failing is not general.

### 2026-08-30 [796e88e9c22d]

- **The blindness was structural, not an oversight.** Every scorer here — `visual_agent`, `score_foreedge`, `score_head_regions`, `score_argument_agent` — iterates over *adjudicated gold entries* and asks what the agent named each one. That loop cannot visit a box that was never drawn. `plate_screen` gets closer but reads `bundle.json`, so it's blind at one remove. Seven leaves are missing their entire scripture column and **not one of them could move a published number**.
- **The fix is to change what the instrument reads.** Unclaimed ink — ink the page prints that no region claims — is a fact about the leaf and the layout together, so it needs no gold to observe.
- **A predicted null is worth as much as a predicted hit.** P3 said in advance that small misses would *not* separate. Confirming it converts "ink coverage probably can't catch a missing catchword" from an intuition into a measured bound.

### 2026-08-30 [0828bd9d78dc]

- **Surya's layout model is RF-DETR** — a DETR-family detector on a DINOv2 backbone (`common/rfdetr/models/lwdetr.py`). The install ships **inference only**: no `SetCriterion`, no `HungarianMatcher`, no loss. But `reinitialize_detection_head(num_classes)` is there and `class_embed` is a plain `nn.Linear(hidden_dim, num_classes)` — the class head is *designed* to be swapped. So the flagged-unverified question resolves to: not fine-tunable as installed, architecturally fine-tunable with upstream training code (not installed either).
- **208 gold leaves are 1.61% of 12,891.** That number governs the whole design.

### 2026-09-04 [71bf596e64f8]

**Jacques told us the answer in its own prompt text:** *"...and a Read() deny rule is configured."* As of CLI **2.1.259**, the *mere existence* of any `Read()`/`Edit()` deny rule makes Claude Code prompt for any Bash command whose target directory it cannot statically resolve. It isn't matching your command against the rule — it's refusing to guess.

**Deny rules outrank `bypassPermissions`.** That's why the launcher's `--permission-mode bypassPermissions` and `--dangerously-skip-permissions` never suppressed this. You cannot flag your way past a deny rule; it has to be removed.

### 2026-09-15 [c98df02774c6]

- **A five-case table beat a happy-path check.** Four of five cases passed on broken code. The one that failed was the only one exercising the fallback branch — the branch that exists *because* the normal path is absent.
- **"Cycle complete" and "lane available" were silently the same variable.** One lock served two questions with different lifetimes; splitting by phase was the whole fix.
- **The same `-s` flag is correct on one field and wrong on the next.** On the pid field it filters garbage; on the epoch field it deletes the case you're handling.

### 2026-09-17 [b222f5cb2ffd]

- **JICM's own HALT makes every transcript end identically.** The actuator tells a lane to save its scratchpad and stop, so every digested transcript's last turn is some variant of *"I've updated `.scratchpad.<lane>.md` and stopped as requested."* That tail is a near-perfect prompt for "write the next assistant turn."
- **The recorded fix addressed the wrong end.** `§2` notes say the earlier instance was fixed by *dropping the opening turns*. The contamination is in the **closing** turns — the part JICM itself writes.
- **The guard is doing its job, and that's the point.** It refused to fold 12–38 words of role-play into a checkpoint. No Silent Degradation means the alert is not the end state though: the successor got *no history at all* on those four cycles.
