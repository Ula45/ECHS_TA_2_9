# Troubleshooting

Problems already met on this project, with the cause and the fix.

## llama-server

**`cudaMalloc failed: out of memory` / `failed to allocate buffer for kv cache`**
The CPU and GPU share 8 GB. Weights, KV cache, compute buffers, the desktop and other programs all compete.
The failed run used `-c 16384 --parallel 4` (a KV cache of about 952 MiB) and still did not fit, which suggests
very little memory was free. Swap does not help because CUDA allocations cannot be paged out.
Fix: start with `./scripts/start_llama_server.sh 3b-1slot`, check free memory (`free -h`, `jtop`), close other programs,
consider headless mode, then raise slots one at a time.

**Model file not found / wrong path**
Launching from `~/ECHS_PRAC2/llama.cpp` means the model is at `../models/<file>.gguf`. The profile script uses full paths from `MODELS_DIR`.

**A flag is rejected (`-fa`)**
llama.cpp changes flag syntax between versions. This board's build uses `-fa on`. Check `./build/bin/llama-server --help`.

**Is it using the GPU?**
The startup log should mention a CUDA device and offloaded layers. In `tegrastats` or `jtop` the GPU load (`GR3D_FREQ`) should rise during generation.
`ldd build/bin/llama-server | grep -i cuda` should list CUDA libraries.

## Python and pip

**`pip install` times out (`ReadTimeoutError` from pypi.org / files.pythonhosted.org)**
PyPI is very slow from this board (about 10 KB/s seen) while GitHub is fast. Use
`--default-timeout=300 --retries=10` (`scripts/setup_venv.sh` does this), try a mirror, or build a wheelhouse on another computer
(`pip download -r requirements.txt -d wheels`, Python 3.12 and aarch64 must match) and install with `--no-index --find-links wheels`.

**`error: externally-managed-environment`**
Ubuntu 24.04 blocks system-wide pip installs. Use the virtualenv and run pip **without sudo**. `sudo pip` ignores the venv.
For jtop only: `sudo pip3 install --break-system-packages -U jetson-stats` (then reboot or log out), or use `tegrastats`.

## cloudflared

**`dpkg: error: cannot access archive 'cloudflared-linux-arm64.deb'`**
The file was never downloaded. `wget https://github.com` saves only the homepage (`index.html`). Use `scripts/install_cloudflared.sh`,
which downloads the real release, checks that it is a Debian package, then installs it. Delete stray files with `rm -f index.html index.html.*`.

**The public URL changes**
Quick tunnels get a new random address on every start. A permanent address needs a named tunnel and a domain.

## Gateway and UI

| Symptom | Cause and fix |
|---|---|
| UI sidebar says "Gateway is offline" | Gateway not running on 8000 or `GATEWAY_URL` wrong |
| UI says "model server is down" | Start llama-server, check `curl http://127.0.0.1:8080/health` |
| HTTP 401 | `GATEWAY_KEY` differs between gateway and UI. Both read `.env` through the start scripts |
| HTTP 429 "busy" | More than `MAX_INFLIGHT` requests. Raise it, or add slots if memory allows |
| HTTP 429 "too many messages" | Session exceeded `RATE_LIMIT_PER_MIN` |
| HTTP 503 | Gateway cannot reach llama-server |
| Replies stop mid-way | `max_tokens` reached (`MAX_TOKENS_CAP`), or context full. Reduce history or raise per-slot context |
| Slow first token with long chats | Prefill of a long prompt. Lower `MAX_HISTORY_MESSAGES` |

## Headless mode (optional memory saving)

```bash
hostname -I                                   # note the IP and confirm SSH works from another computer first
sudo systemctl isolate multi-user.target      # stops the desktop now, reboot brings it back
free -h                                       # compare with before
sudo systemctl set-default multi-user.target  # make permanent (undo: set-default graphical.target)
```

## Power and clocks

```bash
sudo nvpmodel -q                  # current mode
grep -i -E "POWER_MODEL|NAME" /etc/nvpmodel.conf   # available modes (numbering depends on JetPack)
sudo jetson_clocks                # lock clocks at the maximum of the current mode
sudo jetson_clocks --show
```
Mode 0 was seen as 15 W on this board. Higher modes may exist; check the file before switching and watch temperature.
