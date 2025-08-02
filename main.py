import os
import re


GENERATOR = os.environ.get("GENERATOR", "plain")
VALID_GENERATORS = [
    'plain',
]
if GENERATOR not in VALID_GENERATORS:
    raise ValueError(f"GENERATOR is {GENERATOR}, but expecting one of: {VALID_GENERATORS}")


from importlib import import_module
generate = getattr(import_module(GENERATOR), "generate")


def is_valid_components(s: str) -> bool:
    pattern = r'^(V|S|M)(,\s*(V|S|M)){0,2}$'
    if not re.fullmatch(pattern, s):
        return False
    components = [comp.strip() for comp in s.split(',')]
    return len(set(components)) == len(components)


if __name__ == "__main__":

    # Load environment variables
    title = os.environ.get("SPELL_NAME", "Spell Name")
    # TODO: Increase this and prepare for two-line spells
    MAX_TITLE_CHARS = 23
    if len(title) > MAX_TITLE_CHARS:
        raise ValueError(f"Title {title} is too long. Max allowed: {MAX_TITLE_CHARS} chars")
    casting_time = os.environ.get("CASTING_TIME", "")
    # TODO: Add a character limit check
    spell_range = os.environ.get("RANGE", "")
    # TODO: Add a character limit check

    components = os.environ.get("COMPONENTS", "")
    if not is_valid_components(components):
        raise ValueError("Components can only be: V, S, M, separated by comma and not repeated.")
    components = ', '.join([c.strip() for c in components.split(',')])

    duration = os.environ.get("DURATION", "")
    # TODO: Add a character limit check
    description = os.environ.get("DESCRIPTION", "")
    # TODO: Add a character limit check
    school = os.environ.get("SCHOOL", "")
    # TODO: Add a character limit check
    level = int(os.environ.get("LEVEL"))
    if not 0 <= level <= 9:
        raise ValueError(f"Allowed spell levels: {list(range(10))}")

    generate(title, casting_time, spell_range, components, duration, description, school, level)
