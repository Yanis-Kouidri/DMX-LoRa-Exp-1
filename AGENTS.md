# AGENTS.md

## Context

This repository supports an experiment for a PhD thesis (CIFRE) with IRIT on data collection in wireless sensor networks. The goal is a main-track conference paper, so keep peer review in mind: favour rigorous methodology, reproducibility, traceable measurements and claims that the data can support. See `docs/plan-experimental.md` for the research question and hypotheses.

## Structure

- `Mote/`: Contains a Python 3.14 project managed with `uv`. These files are written to communicate with the Microchip RN2483 LoRa Technology Mote in order to send instructions to it.
- `LoRaWAN-Infra/`: Contains a docker-compose file and configuration files to run the LoRaWAN stack.
- `docs/`: Experiment documentation (experimental plan, deployment locations, fixed gateway).
- `secrets-example.md`: A template file used to structure secrets safely.

## Guardrails

- Never commit a decrypted secret.
- Always use conventional commit messages.