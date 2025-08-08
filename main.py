import os
from importlib import import_module

from spell import Spell

GENERATOR = os.environ.get("GENERATOR", "plain")
VALID_GENERATORS = [
    "plain",
]
if GENERATOR not in VALID_GENERATORS:
    raise ValueError(
        f"GENERATOR is {GENERATOR}, but expecting one of: {VALID_GENERATORS}"
    )


generate = getattr(import_module(GENERATOR), "generate")


if __name__ == "__main__":

    spell = Spell(
        os.environ.get("SPELL_NAME", ""),
        os.environ.get("CASTING_TIME", ""),
        os.environ.get("RANGE", ""),
        os.environ.get("COMPONENTS", ""),
        os.environ.get("DURATION", ""),
        os.environ.get("DESCRIPTION", ""),
        os.environ.get("SCHOOL", ""),
        int(os.environ.get("LEVEL")),
    )

    generate(spell)
