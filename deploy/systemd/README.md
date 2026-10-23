# systemd units (optional)

These start the stack automatically at boot. Check the paths first: they assume the user
`jetson3`, the project in `/home/jetson3/ECHS_PRAC2/jetson-edge-llm-chat`, and the venv in
`/home/jetson3/ECHS_PRAC2/venv`. Confirm `jetson_clocks` is at `/usr/bin/jetson_clocks` with `which jetson_clocks`.

```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llama-server gateway frontend      # add jetson-clocks if wanted
systemctl status llama-server gateway frontend
journalctl -u gateway -f                                       # live logs
```

To change the model profile, edit the profile name in `llama-server.service`, then
`sudo systemctl daemon-reload && sudo systemctl restart llama-server`.

The Cloudflare quick tunnel is deliberately not a service: its URL changes on every start.
For a permanent URL, create a named tunnel (needs a Cloudflare account and a domain) and run it as a service.
