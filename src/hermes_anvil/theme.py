"""Hatch theming: palette, ASCII art, and small text helpers shared
across screens. Kept separate from the screens themselves so the "hatch
your own agent" voice stays consistent without duplicating strings.
"""

from __future__ import annotations

ANVIL_ART = r"""
        ________________
       /                \
  ____/   HERMES ANVIL   \____
  \__________________________/
           |        |
         __|________|__
        /______________\
"""

HATCH_ART = r"""
              .--.
           .-(    ).
          (___.__)__)
              | |
          ____| |____
         /  YOUR AGENT \
        /   HAS HATCHED  \
        \________________/
"""

# Textual CSS variable overrides -- warm anvil-orange accent on a dark
# forge background, readable in both light and dark terminals.
PALETTE = {
    "primary": "#e07a2c",
    "primary-lighten-2": "#f4b183",
    "background": "#161311",
    "surface": "#221c18",
    "success": "#5fb87a",
    "warning": "#e0b52c",
    "error": "#d9534f",
}

WELCOME_TAGLINE = "Hatch your own agent."

STEP_LABELS = {
    "preflight": "Checking your GCP account",
    "name_your_agent": "Naming your agent",
    "project_setup": "Setting up your project",
    "api_enable": "Enabling required APIs",
    "service_account": "Creating a service account",
    "network_security": "Setting up secure networking",
    "secret_setup": "Storing your API key securely",
    "vm_provision": "Provisioning your agent's home",
    "hermes_install_wait": "Incubating",
    "hatch_reveal": "Hatching",
    "handoff_summary": "Wrapping up",
}
