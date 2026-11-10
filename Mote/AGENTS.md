# AGENTS.md

## Mote access

- Each RN2483 mote is driven by a Raspberry Pi: mote N is on `pi-mote-N`
  (`pi-mote-1` to `pi-mote-6`), reachable over Tailscale with `ssh pi@pi-mote-N`.
- The mote is on `/dev/ttyACM0`. The repository is cloned in `~/DMX-LoRa-Exp-1`;
  run scripts from `~/DMX-LoRa-Exp-1/Mote` with `uv run python src/<script>.py`.
- Update a Pi clone with `git pull --ff-only` only.
- The PPK2 energy bench uses a separate Pi, `pi-ppk2` (Raspberry Pi 5), which
  drives the test mote over its own UART (`/dev/ttyAMA0`), not USB. The PPK2
  itself is on the Windows PC. Run the bench from WSL with
  `uv run python src/banc_ppk2.py`; see `banc-ppk2.md`.
- On `pi-ppk2`, GPIO14 (TX) must stay an input (`pinctrl set 14 ip pn`) unless
  the PPK2 is powering the mote; `banc_pi.py` handles this during a run.

## Guardrails

- Only one process can use the serial port: check that no script (campaign,
  terminal) is already running on the Pi before talking to the mote. This
  includes the `regime-1a.service` user unit (`systemctl --user status
  regime-1a.service`); never stop it on a deployed mote without the user's
  approval, as it collects phase 1 measurements.
