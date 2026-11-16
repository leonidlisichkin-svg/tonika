# Working in a Codespace

Tonika is developed in [GitHub Codespaces](https://github.com/features/codespaces): VS Code in a
browser tab, running on GitHub's machine. Nothing is installed on your computer, and the work is
there again from any other computer. The environment is described in
[`.devcontainer/`](../.devcontainer/devcontainer.json): Python 3.13, uv, Node, the GitHub CLI,
Claude Code, the project with its Russian pack and models.

## Open it

1. On the repository page press **Code**, choose the **Codespaces** tab, press
   **Create codespace on main**.
2. Wait. The first start takes several minutes: the container is built, the dependencies are
   installed and the Russian models (about 500 MB) are downloaded. The terminal at the bottom
   ends with `Tonika is ready.`
3. Next time, open the same codespace from the same **Codespaces** tab: it starts in seconds and
   everything is where you left it.

## Start Claude Code

1. Press the Spark icon: at the top right of the editor while a file is open, or in the bar on
   the left edge, where it is always visible.
2. The first time, sign in with your Claude account in the browser tab that opens. If the tab
   shows a code, copy it and paste it where VS Code asks for it.
3. Choose the model with `/model`.
4. Write what you want. To take the next task from the plan, write: **«Продолжай по плану»**.

Claude reads [`CLAUDE.md`](../CLAUDE.md) at the start of every conversation: the rules of the
project, the commands, and how a session ends (one small pull request with green CI).

The same Claude Code runs in the terminal as `claude`, with the same sign-in.

## Try Tonika

In the terminal (**Terminal → New Terminal**):

```bash
uv run tonika annotate --target plus "В старом замке сломался замок."
uv run pytest -m "not models"          # offline tests, a few seconds
uv run pytest -m models                # tests with the real models
uv run tonika eval data/golden/ru.txt  # accuracy on the golden set
```

To run a script of your own, drag the text file into the file list on the left, then:

```bash
uv run tonika annotate -f script.txt -o marked.txt --target plus --review check.md
```

## Good to know

- **Allowance.** A personal GitHub account includes 120 core-hours of Codespaces a month: 60 hours
  on the default 2-core machine. A codespace stops by itself after 30 minutes without activity;
  a stopped codespace uses no hours, only a little of the free storage. Usage: github.com →
  Settings → Billing and plans.
- **Your work is safe when it is pushed.** A stopped codespace keeps its files, but GitHub deletes
  codespaces left unused for 30 days. Everything that matters lives in pull requests.
- **Signing in again.** Claude's sign-in survives stopping and starting. After a rebuild of the
  container (rare: only when `.devcontainer/` changes) sign in once more.
- **Rebuild.** If `.devcontainer/` changed, VS Code offers **Rebuild**. Agree, and wait as on the
  first start.
- **Permissions.** [`.claude/settings.json`](../.claude/settings.json) lets Claude run the
  project's own checks (`uv run …`) and read pull request status without asking each time.
  Committing, pushing and opening a pull request still ask for your approval.
