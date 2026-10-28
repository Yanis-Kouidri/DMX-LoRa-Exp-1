# AGENTS.md

## Mote access

- Each RN2483 mote is driven by a Raspberry Pi: mote N is on `pi-mote-N`
  (`pi-mote-1` to `pi-mote-6`), reachable over Tailscale with `ssh pi@pi-mote-N`.
- The mote is on `/dev/ttyACM0`. The repository is cloned in `~/DMX-LoRa-Exp-1`;
  run scripts from `~/DMX-LoRa-Exp-1/Mote` with `uv run python src/<script>.py`.
- Update a Pi clone with `git pull --ff-only` only.

## Guardrails

- Only one process can use the serial port: check that no script (campaign,
  terminal) is already running on the Pi before talking to the mote. This
  includes the `regime-1a.service` user unit (`systemctl --user status
  regime-1a.service`); never stop it on a deployed mote without the user's
  approval, as it collects phase 1 measurements.
