import re

class Spell:
    """
    Represents a Dungeons & Dragons spell with key attributes and validation.

    Attributes:
        MAX_TITLE_CHARS (int): Maximum character length allowed for the spell title.
        title (str): Name of the spell.
        casting_time (str): Time required to cast the spell.
        range (str): Effective range of the spell.
        components (str): Spell components (V, S, M), validated and formatted.
        duration (str): Duration of the spell's effect.
        description (str): Text description of the spell's effect and mechanics.
        school (str): The magical school the spell belongs to (e.g., Evocation).
        level (int): Spell level, must be between 0 (cantrip) and 9 (highest level).
    """
    # TODO: Increase this and prepare for two-line spells
    MAX_TITLE_CHARS = 23
    MAX_DESCRIPTION_CHARS = 650
    def __init__(
        self,
        title: str,
        casting_time: str,
        spell_range: str,
        components: str,
        duration: str,
        description: str,
        school: str,
        level: int
    ):
        """
        Initialize a Spell object with validation checks on title length, component format, and level.

        Raises:
            ValueError: If title exceeds MAX_TITLE_CHARS.
            ValueError: If components are not one or more of 'V', 'S', or 'M', comma-separated and unique.
            ValueError: If level is not between 0 and 9.
        """
        if len(title) > Spell.MAX_TITLE_CHARS:
            raise ValueError(f"Title {title} is too long. "
                             f"Max allowed: {Spell.MAX_TITLE_CHARS} chars")
        self.title = title
        # TODO: Add a character limit check to casting time.
        self.casting_time = casting_time
        # TODO: Add a character limit check to spell range
        self.range = spell_range
        if not self.is_valid_components(components):
            raise ValueError("Components can only be: V, S, M, separated by comma and not repeated.")
        self.components = ', '.join([c.strip().upper() for c in components.split(',')])
        # TODO: Add a character limit check to duration
        self.duration = duration
        if len(title) > Spell.MAX_DESCRIPTION_CHARS:
            raise ValueError(f"Description is too long. "
                             f"Max allowed: {Spell.MAX_DESCRIPTION_CHARS} chars. "
                             f"Current: {len(description)} chars.")
        self.description = description
        # TODO: Add a character limit check to school.
        self.school = school
        if not 0 <= level <= 9:
            raise ValueError(f"Allowed spell levels: {list(range(10))}")
        self.level = level

    @staticmethod
    def is_valid_components(s: str) -> bool:
        """
        Validates that the components string contains only V, S, and M, comma-separated, and not repeated.

        Args:
            s (str): The raw components string to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        pattern = r'^(V|S|M)(,\s*(V|S|M)){0,2}$'
        if not re.fullmatch(pattern, s):
            return False
        components = [comp.strip() for comp in s.split(',')]
        return len(set(components)) == len(components)


