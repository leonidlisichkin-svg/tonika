# Working in a Codespace

Tonika is developed in [GitHub Codespaces](https://github.com/features/codespaces): VS Code in a
browser tab, running on GitHub's machine. Nothing is installed on your computer, and the work is
there again from any other computer. The environment is described in
[`.devcontainer/`](../.devcontainer/devcontainer.json): Python 3.13, uv, Node, the GitHub CLI,
Claude Code, the project with its Russian pack and models.

## Open it

1. On the repository page press **Code**, choose the **Codespaces** tab, press
   **Create codespace on main**.
2. Wait a few minutes. The window opens early, reloads once by itself, and the terminal at the
   bottom shows `Running postCreateCommand…` while the dependencies and the Russian models (about
   500 MB) are installed. It is ready when that terminal is replaced by an ordinary prompt
   ending in `$`. Do not type commands before that.
3. Next time, open the same codespace from the same **Codespaces** tab: it starts in seconds and
   everything is where you left it.

## Start Claude Code

1. Press the Claude icon (an orange spark) in the bar on the left edge. It appears once the
   setup above has finished.
2. The first time, press the sign-in button and then **Authorize** in the browser tab that opens.
3. If that tab then says **"This site can't be reached"** at an address starting with
   `localhost`, the sign-in is one step from done. The answer was sent to your own computer, and
   Claude is waiting for it on the codespace. Hand it over:
   - click the address bar of that tab and copy the whole address (Ctrl+C);
   - go back to the codespace tab and click in the terminal after the `$`;
   - type `curl "`, paste the address (Ctrl+V), type `"`, press Enter.

   The Claude panel now shows your account.
4. Press **New session**, choose the model with `/model`, and write what you want. To take the
   next task from the plan, write: **«Продолжай по плану»**.

The **Chat** panel on the right edge belongs to GitHub Copilot, not to Claude. Close it with
the cross in its corner.

Claude reads [`CLAUDE.md`](../CLAUDE.md) at the start of every conversation: the rules of the
project, the commands, and how a session ends (one small pull request with green CI).

The same Claude Code runs in the terminal as `claude`, with the same sign-in.

## Try Tonika

Click in the terminal, paste a line, press Enter:

```bash
uv run tonika annotate --target plus "В старом замке сломался замок."
uv run pytest -m "not models"          # offline tests, a few seconds
uv run pytest -m models                # tests with the real models
uv run tonika eval data/golden/ru.txt  # accuracy on the golden set
```

The first line answers `В старом з+амке сломался зам+ок.` A long warning from `onnxruntime`
about `GetPciBusId` above the answer is harmless.

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
