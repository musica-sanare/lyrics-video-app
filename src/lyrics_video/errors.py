"""Errors with messages meant for the user."""


class LyricsVideoError(Exception):
    """Base class of every error this app reports to the user."""


class ConfigError(LyricsVideoError):
    """The song file is missing, unreadable or invalid."""


class LyricsError(LyricsVideoError):
    """A lyrics or text file cannot be read or has an invalid line."""


class FontError(LyricsVideoError):
    """A font file cannot be found or opened."""


class CaptionError(LyricsVideoError):
    """A caption cannot be drawn, for example because it does not fit."""


class OutputExistsError(LyricsVideoError):
    """Output files exist and overwriting was not allowed."""
