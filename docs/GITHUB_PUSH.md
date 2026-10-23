# Put the project on GitHub (and add the link to your Excel sheet)

Replace `<Ula45>` and `<jetson-ip>` with your own values.

## Step 0: get the project onto the Jetson and open it in VS Code

Copy the zip from your laptop to the board (PowerShell on Windows, Terminal on macOS/Linux):

```bash
scp jetson-edge-llm-chat.zip jetson3@<jetson-ip>:~/ECHS_PRAC2/
```

Then on the Jetson (over SSH):

```bash
cd ~/ECHS_PRAC2
sudo apt install -y unzip     # only if unzip is missing
unzip jetson-edge-llm-chat.zip
cd jetson-edge-llm-chat
```

To edit the files in VS Code on your laptop while they live on the Jetson: install the **Remote - SSH** extension,
choose *Remote-SSH: Connect to Host*, enter `jetson3@<jetson-ip>`, then *File > Open Folder* and pick
`/home/jetson3/ECHS_PRAC2/jetson-edge-llm-chat`. The built-in terminal then runs on the Jetson.

## Step 1: create an empty repository on GitHub

1. Sign in at github.com and choose **New repository**.
2. Name it `jetson-edge-llm-chat`.
3. Choose Public or Private.
4. **Do not** tick "Add a README", ".gitignore" or "license". The project already has them, and an empty repository avoids merge conflicts.
5. Click **Create repository** and copy the HTTPS address, for example `https://github.com/<Ula45>/jetson-edge-llm-chat.git`.

## Step 2: commit and push from the project folder

```bash
cd ~/ECHS_PRAC2/jetson-edge-llm-chat
git init -b main
git config user.name  "Your Name"
git config user.email "you@example.com"      # use the email linked to your GitHub account

git add .
git status                                   # CHECK: no .env, no .gguf files, no venv/ folder in the list
git commit -m "Jetson edge LLM chat: gateway, UI, benchmarks, docs"

git remote add origin https://github.com/<Ula45>/jetson-edge-llm-chat.git
git push -u origin main
```

Safety check before pushing: `git check-ignore -v models/test.gguf .env` should print the matching `.gitignore` rules.
Model files are several GB and GitHub rejects files over 100 MB.

## Step 3: sign in when asked

GitHub no longer accepts your account password for pushes. Pick one method:

- **Personal access token (simplest).** On GitHub: *Settings > Developer settings > Personal access tokens*. Create a
  fine-grained token limited to this repository with **Contents: Read and write**. When `git push` asks for a password, paste the token.
- **GitHub CLI.** `sudo apt install gh` then `gh auth login` and follow the prompts.
- **SSH key.** `ssh-keygen -t ed25519 -C "you@example.com"`, add `~/.ssh/id_ed25519.pub` under *Settings > SSH and GPG keys*, then
  `git remote set-url origin git@github.com:<Ula45>/jetson-edge-llm-chat.git`.

Treat a token like a password. Never paste it into a file in the repository. If you ever commit a secret, revoke it on GitHub right away.

## Step 4: add your evidence, then push again

After you capture screenshots, text evidence and a video (see `EVIDENCE_CHECKLIST.md`):

```bash
git add docs/screenshots docs/evidence benchmarks/results.csv README.md
git commit -m "Add execution evidence and benchmark results"
git push
```

**Screenshots**: save PNG files in `docs/screenshots/` with the names used in the README.

**Video** (pick one):
- *Easiest on GitHub:* open the README on github.com, click the pencil (edit), drag your `.mp4` into the editor. GitHub uploads it and inserts a
  `https://github.com/user-attachments/assets/...` link on its own line; it plays inline. Commit the change. Size limits apply
  (about 10 MB on free accounts at the time of writing; check GitHub's current limit).
- *Upload to YouTube (unlisted) or Google Drive* and paste the link into the "Demo video" line of the README.
- *GIF:* `ffmpeg -i demo.mp4 -vf "fps=8,scale=800:-1" docs/demo.gif`, then add `![demo](docs/demo.gif)` to the README.

## Step 5: add the repository link to Excel

1. Open the repository page on GitHub and copy the address from the browser, for example
   `https://github.com/<Ula45>/jetson-edge-llm-chat`.
2. Paste it into the correct cell in the Excel sheet. To make it clickable, select the cell and press **Ctrl+K** (Insert Link), or use `=HYPERLINK("https://github.com/<Ula45>/jetson-edge-llm-chat","GitHub repo")`.
3. If the repository is **Private**, the person checking it needs access. Either make it Public or add them under *Settings > Collaborators*.

## Quick reference

| Task | Command |
|---|---|
| See what changed | `git status` and `git diff` |
| Save a snapshot | `git add . && git commit -m "message"` |
| Upload | `git push` |
| Download others' changes | `git pull` |
| Undo staging of a file | `git restore --staged <file>` |

