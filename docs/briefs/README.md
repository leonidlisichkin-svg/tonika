# Briefs

One brief is one pull request. Take them in roadmap order; the number is the roadmap item.

| Brief | Needs Leo |
| --- | --- |
| [0.1 Listening test](0.1-listening-test.md) | Five minutes of listening in Fliki |
| [1.1 Script trial](1.1-script-trial.md) | A real script, a voiced episode, a list of wrong words |
| [1.2 Model comparison](1.2-model-comparison.md) | Nothing |
| [2.1 HTTP API](2.1-http-api.md) | Nothing |
| [2.2 Browser core](2.2-browser-core.md) | Nothing |
| [2.3 Editor screen](2.3-editor-screen.md) | A look on his phone |
| [2.4 Review flow](2.4-review-flow.md) | A look on his phone |
| [2.5 Docker and hosting](2.5-docker-hosting.md) | The choice of hosting and an account |
| [3.1 Example checks](3.1-example-checks.md) | Nothing |
| [3.2 Seed examples](3.2-seed-examples.md) | Reading a sample as a native speaker |
| [3.3 Decision lists](3.3-decision-lists.md) | Nothing |
| [3.4 Corrections layer](3.4-corrections-layer.md) | Nothing |

Items without a brief (the rest of Phase 3, Phase 4 and later) have a spec in
[`docs/specs/`](../specs/). Their first pull request is the brief itself.

## How a session goes

1. Read `CLAUDE.md`, `docs/ROADMAP.md`, then the brief and every file under its "Read first".
2. Tell Leo in two or three sentences, in Russian, what will be built and what he will see at the
   end. If the brief names something he must decide or do, ask that first, one step at a time.
3. Branch from an up-to-date `main`. Build with tests. Run the four checks from `CLAUDE.md`.
4. Open the pull request. Wait for CI. Fix what is red.
5. Tick the item in `docs/ROADMAP.md` in the same pull request. Record decisions in
   `docs/DECISIONS.md`.
6. Tell Leo exactly what to press to merge, and close with the three lines from `CLAUDE.md`.

## What a brief may not override

The principles in `CLAUDE.md`. If a brief and a principle disagree, the principle wins and the
brief is corrected in the same pull request. If a brief disagrees with the code as it now is,
trust the code, say so, and adjust.
