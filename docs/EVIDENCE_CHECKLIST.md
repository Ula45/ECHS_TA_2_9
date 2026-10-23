# Execution evidence checklist

Capture these while the system is running and save them in `docs/screenshots/`.
Do not show your `GATEWAY_KEY`, tokens or passwords in any capture.

Already captured (22 Oct 2026) and used in the README: `architecture_diagram.png`, `hardware_setup.png`,
`htop_system_load.png`, `llama_server_slot_logs.png`, `public_url_chat.png`, `jtop_model_loaded.png`.

Still to capture:

| File | What to show | How |
|---|---|---|
| `jtop_during_generation.png` | jtop **while a reply is streaming**: GPU %, GPU clock, EMC, power, temperature | `sudo jtop`, then send a long question from the UI |
| `llama_server_start.png` | Terminal with the profile line, CUDA device lines, the exact `-c` and `--parallel` values and "listening on 127.0.0.1:8080" | `./scripts/start_llama_server.sh 3b-2slot` |
| `gateway_log.png` | Gateway log with request lines (`req=... ttft=... tokens=...`) | `./scripts/start_gateway.sh` |
| `ui_two_tabs.png` | Two browser windows side by side, each with a different conversation streaming at the same time | Open `http://<jetson-ip>:8501` twice |
| `benchmark_output.png` | Benchmark table for 1, 2 and 4 users | `python benchmarks/bench.py ...` |
| `public_url_phone.png` | The chatbot opened from a phone on mobile data | `./scripts/start_tunnel.sh`, open the printed URL |

After saving a new image, add it to the README with `![caption](docs/screenshots/<file>.png)`.

## Text evidence

```bash
./scripts/collect_evidence.sh      # writes system_state.txt, gateway_api.txt, sample_chat.txt, tegrastats_sample.txt to docs/evidence/
```

Also keep `benchmarks/results.csv` and the tegrastats logs from `./scripts/monitor.sh <label>`.

## Video (about 60 to 120 seconds)

Suggested order:
1. `./scripts/check_env.sh` or jtop: show the board and that nothing is hidden.
2. Start llama-server, gateway and UI (three terminals visible).
3. Two browser windows asking different questions at the same time; both answers stream.
4. jtop beside them showing GPU load and power during generation.
5. Run the benchmark for 1, 2 and 4 users.
6. Open the public URL on a phone.

Recording: Windows `Win+G` (Xbox Game Bar) or OBS Studio; macOS `Shift+Cmd+5`; a phone screen recorder for the public URL step.
Keep the file small (under about 10 MB for GitHub upload) or link to YouTube or Drive instead.

## Honest reporting

Include failures that you hit and fixed (for example the out-of-memory error with four slots). They show real engineering and explain your final settings.
Report measured numbers only, and note the configuration (profile, context, slots, power mode, whether the desktop was running).
