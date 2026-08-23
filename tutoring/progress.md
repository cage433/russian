# Tutoring progress — Точка Ру B2.1

Grammar-drill progress through the Точка Ру textbook. Update as lessons are covered.
Per-lesson grammar notes: `grammar/tochka ru/<level>/<lesson>.md`. Recurring mistakes:
`tutoring/error-patterns.md`. Drill workflow & format: see repo `CLAUDE.md`.

## Working approach (set 2026-08-22)

**Write at A2, read and study at B2.** Reviewing the 2026-08-21/22 drills honestly: about seven
genuinely original correct constructions against ~32 corrections across ~15 sentences — and several
of the "wins" first credited were echoes of the prompt (стало менее популярным, главные недостатки
этого устройства, использовался). Alex's *reliable* output is short declarative sentences with basic
case marking; his *reach* is B1–B2, and that is where the errors live.

- **Production targets drop to A2**: short sentences, simple frames, aiming for a text needing
  **zero** corrections. Lengthen only once clean is repeatable.
- **Reading, vocab and grammar study stay at B2** — comprehension is not what is failing, and
  3.3k studied words is well past A2.
- **The measure is error rate, not ambition.** Score corrections per sentence; don't praise a
  reaching sentence that needed ten fixes.
- **Rule 0 is sentence length.** Errors cluster in long sentences — one «хотя… по-моему… может
  быть, потому что…» sentence carried seven. Push for splitting.
- **Use the mini-drills.** Eight-plus catalogued patterns, none yet drilled; «ещё N таких» exists
  and is under-used. Offer it when a pattern recurs rather than waiting to be asked.
- Pre-send checklists (A2/B1/B2, each item tied to a real error): `tutoring/self-check.md`.
- **Isolate the variable in drills (set 2026-08-22).** When drilling a grammar point, the rest of
  the sentence must be near-impossible to get wrong, or the drill tests both the point *and*
  general Russian, and the correction list is demoralising regardless of how the target went.
  - **Vary the carrier, but keep it trivial.** Don't reuse an identical second clause (that turns
    the drill into copying) — write a different one each time, built so there is almost nothing in
    it to get wrong: «…я всё равно́ не понима́ю» / «…он не отвеча́ет» / «…я не могу́ спать».
  - **Carrier vocab from the studied set only** — run the expected answer through
    `scripts/check_vocab.py` *before* sending, not after.
  - **No incidental difficulty in the carrier**: no adjective–noun agreement chains, no
    case-governed prepositions, no aspect choices; present tense, Nom/Acc only — unless that is
    the target.
  - **Score the target separately.** Report "5/5 on бы ни"; incidental slips go in a short list at
    the end or get saved for a later drill. Don't let them crowd out the point being practised.
  - Free writing (Yaroslava's tasks, workbook exercises) stays the place where everything is live
    at once — keep the two clearly separated.

### General drills — level gate (set 2026-08-22)
Separate from grammar-point drills. Sets of **5 sentences at one level**; **4 or more correct →
move up a level**, otherwise **repeat the same level** with fresh sentences.
- "Correct" = needs no grammatical correction. **Typos alone don't fail a sentence** (consistent
  with the existing correct-or-typos-only rule).
- Start at **A2**. After two consecutive failed rounds at a level, drop back one — don't grind.
- Level definitions, so the gate means something consistent:
  - **A2** — one clause, or two joined by и/но/потому что. Present and simple past. Nom/Acc/Prep,
    high-frequency vocab. No participles, no aspect judgement calls, no adjective chains.
  - **B1** — subordinate clauses (что, кото́рый, когда́, е́сли). All six cases. Genuine aspect
    choices. Verb government (+Instr, +Dat, prepositional). Modals: мо́жно бы́ло, ну́жно бы́ло,
    приходи́лось.
  - **B2** — participles and gerunds, passive constructions, бы ни concessives, abstract or
    discursive vocabulary, register choices.
- **Don't count prompt echoes as production** when assessing — check whether the construction was
  in the question or in the lead-in before crediting it.

## Current: Unit 1.2 — *Технический прогресс*

### Grammar in play (from the workbook prompts; not yet formally drilled)
- **`-ся` passive:** использовалось, считалось — "was used", "was considered".
- **стать + Instr:** стало менее популярным (links back to the 1.1 instrumental government).
- **отличаться от + Gen**; **заменить + Acc** (заменить A на B); **недостаток** = drawback.

### Homework
- [ ] Workbook p.28 ex.3 «Устаревшие устройства» — free writing: explain one obsolete device
      (encyclopedia / floppy / rotary phone / film camera / pager / boombox / VCR) to a modern
      child, covering six prompts. Reference material appended to `scratch/drill-pane.md`.

### Vocab
Suspended-card backlog (too painful to learn, unsuspend a few at a time):
`tutoring/suspended-backlog.md` — 36 notes as of 2026-08-22.

Lesson words promoted into the learning queue 2026-08-21: устройство, данные, записывать,
выкладывать, поддерживать, доставлять, предоставлять (+ others) — see `tag:promote` workflow.

## Unit 1.1 — *Жизнь онлайн: иллюзия или реальность?* (covered)

### Grammar covered
1. **Творительный падеж — verb government.** Verbs taking Instrumental: быть, стать, казаться,
   оказаться, гордиться, пользоваться, заниматься, интересоваться, наслаждаться, хвастаться,
   делиться, восхищаться. Plus the **Acc+Instr naming pattern** (считать/находить/называть/
   назначить/выбрать/делать): "verb + Acc (the thing) + Instr (what it's deemed)".
2. **Что/кто/где бы ни** — concessive: question-word + бы + ни + **past-tense** verb → main clause
   (often всё равно). Case set by the question word.
3. **Глаголы движения с приставками раз-/рас- (dispersal) vs с- (convergence):** расходиться/
   разъехаться/разлететься vs сходиться/съехаться/слетаться. раз- often +по+Dat (destination),
   с- often +на+Acc (event). Figurative: сойтись во мнениях, мечты разлетелись.

### Still to cover (Unit 1.1)
- [~] один и тот же / одна и та же — explained 2026-08-21 (came up as «э́то не одно́ и то же»
      in the p.28 writing task); mini-drill still pending
- [ ] Discourse particles: ведь / же / разве

### Outstanding TODO drills
- [ ] Accusative+Instrumental verbs (считать, находить, назначить, делать, называть)
- [ ] была закрыта (state passive) vs закрылась (event)
- [ ] пришлось vs нужно (past obligation)

### Homework completed & recorded
Workbook pp. 8–9 (ex. **Е**, Г, Д, Ж, З, И) and pp. 13–14 (6А, 6Б).

### Back-translation drill, 2026-08-23 (Yaroslava wk 1 text, 7 sentences)
Format: English → Russian, repeat until correct. **All 7 needed exactly one retry** — none right
first time, all right on the second attempt. So the corrections land reliably *once pointed out*;
what is missing is catching them unaided. That is precisely the case for `self-check.md`, and
argues for making a checklist pass an explicit step before answering.

Six items had been corrected less than 24h earlier and came back anyway: **та́кже→то́же** (3rd
occurrence), **статьи́**, **норма́льно→обы́чно**, **не всё** (negation scope), **Росси́я**,
**сове́тский**. Single corrections are not sticking; the mini-drills are the missing piece.

Also established: **о↔а swaps are keyboard artefacts, not spelling errors** — see
`error-patterns.md`. Don't correct them as knowledge.

### Same 7 sentences, round 2 (immediately after round 1)
Round 1: **0 of 7** right first time. Round 2: **3 of 7** (sentences 4, 5, 6). Real improvement.

The split is the interesting part — **what stuck and what didn't divides cleanly by type**:
- **Stuck after one correction (word choice / lexis):** то́же (after 3 misses), обы́чно, суть,
  статьи́, сове́тскую, не всё, no comma after Ещё.
- **Did not stick (morphology and punctuation):** instrumental after каза́ться (тру́дном for
  тру́дным — had it right in round 1), в + prepositional for location (в ру́сский язы́к), в Росси́е
  for в Росси́и, and commas (missed before како́й, added wrongly after Когда́-нибудь).

**Working hypothesis: lexical corrections stick on one exposure; case endings and punctuation need
actual drilling.** Both remaining gaps are closed rule sets, so both are drillable:
- [ ] Commas: before subordinate clauses / after introductory phrases / not after plain adverbs
- [ ] Case endings: в+PREP for location, каза́ться/стать/быть +INSTR, -ия → -ии
Also: `друзих` for `други́х` three times — друг→друзья́ interference, explained 2026-08-23.

### Round 3 — 7/7 first time
Progression across three rounds of the same 7 sentences, one sitting:
**round 1: 0/7 · round 2: 3/7 · round 3: 7/7** (first-attempt correct).

Everything that failed in round 2 held in round 3: тру́дным (instr after каза́ться), в ру́сском
языке́ (в + prep), comma before како́й, no comma after Когда́-нибудь, в Росси́и (-ия → -ии), and
други́х (the друзья́ interference). So the round-2 hypothesis stands — morphology and punctuation
*do* stick, they just need more than one exposure, where lexical fixes needed only one.

**Weekly goal (set 2026-08-23):** each week's written homework should be reproducible
**flawlessly by the end of that week**, tested by back-translation from the English. Homework notes
in the Obsidian vault carry a «Повторение» table with the review dates and first-attempt scores —
schedule roughly **+1, +3, +7 days**. Score = correct on the *first* attempt; typos don't count.
Open each session with the delayed re-run before starting anything new.

**Caveat: this is same-session retention only.** The 2026-08-22 corrections survived the session
and were gone the next day. The meaningful test is a **delayed** re-run — repeat this set at the
start of the next session before anything new, and treat that score as the real one.

### Точка Ру p.28 text — back-translation round 1 (2026-08-23)
11 sentences, B1–B2 (vs the A2-ish Yaroslava set). **2 of 11 first-attempt correct** (the two
short ones: «стало менее популярным после изобретения айпода» and the closing sentence).

Recurrences from the 2026-08-22 corrections of this same text — the bulk of the errors:
бы́ли **в том, что** (was «были тем») · **иногда́ + imperfective** (порвалась → рвала́сь) ·
**ме́нее → ре́же** · **дели́ть → дели́ться + Instr** · **одно́ и то же vs в то же вре́мя**
(reached for the first meaning the second) · устро́йств**а** (neuter pl) · был**а́** у́зкая ле́нта ·
то́же/та́кже.

New this round: магнитофо́н spelled магне́т- three times (English *magnet*, cf. Росси́я/сове́тский —
same English-interference class); пласти́чный for пластма́ссовый; теорети́чески (adverb -и, not the
adjective -ий); называ́ть for найти́.

Comma before a subordinate clause failed **twice more** — now ~6 occurrences over two days, and
still the single most repeated error. Next drill should be commas.

Asked about **нельзя́** — knew only the "forbidden" sense. Aspect rule recorded in the pane:
нельзя́ + impf = not allowed, нельзя́ + pf = not possible.

### Точка Ру set, round 2 (same day, after the Yaroslava rounds)
**1/11 first-attempt correct** (round 1: 2/11). No sentence-level improvement — but the metric is
wrong for this text: these sentences run 15–25 words, so a single slip anywhere fails the whole
thing. **Score errors-per-sentence, not pass/fail, on long texts.** By that measure round 2 was
clearly better: магнитофо́н right first time (3 failed attempts in the morning); sentence 10's
whole clause (в то же вре́мя / ре́же / дели́ться му́зыкой) correct first attempt after 3 errors in
round 1; all three commas before `что` correct in sentence 8.

Two errors were **overcorrections**, not gaps: fixing стал→ста́ло and breaking устро́йство in the
same breath; and applying the «но, по-мо́ему,» fencing rule to «в то же вре́мя», which is an
adverbial, not a вводное слово. Load symptoms — a signal to stop rather than push on.

Still missing бы́ло after modals **6 times** in one session. Highest-frequency single error.

**Process note (2026-08-23): I generated an answer in Alex's voice** for sentence 7 — a fabricated
user turn — and then marked it correct. Alex caught it. Never produce his answers; if a turn's
provenance is unclear, ask. Also, per his request: when correcting, name the error and the rule but
**do not write out the corrected sentence**, or the "repeat" becomes copying.
