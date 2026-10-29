"""Text bindings update native widgets without rebuilding their state or connections."""
from .i18n import TEXT
VALUE_KEYS = {value: key for key, pair in TEXT.items() for value in pair if '{' not in value}

def bind(widget, value, role=None):
    widget.setProperty('ffTextKey', VALUE_KEYS.get(value))
    if role: widget.setProperty('ffRole', role)
    return widget

def bind_key(widget, key, **values):
    widget.setProperty('ffTextKey', key)
    widget.setProperty('ffTextValues', values)
    return widget

def role(callback):
    return {'change_theme': 'theme', 'change_language': 'language'}.get(getattr(callback, '__name__', ''))
