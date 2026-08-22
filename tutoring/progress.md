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
