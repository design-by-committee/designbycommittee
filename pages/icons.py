"""Line icons for Icon grid sections: 24×24, drawn with a 2px round stroke in the current text colour."""

from django.utils.html import format_html
from django.utils.safestring import mark_safe

ICONS = {
    "calendar": ("Calendar", '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
    "calendar-x": (
        "Calendar with a cross",
        '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M10 13.5l4 4M14 13.5l-4 4"/>',
    ),
    "lineup": (
        "People (lineup)",
        '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
        '<path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.3c2.1.7 3.5 2.8 3.5 5.7"/>',
    ),
    "star": ("Star", '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/>'),
    "qr": (
        "QR code",
        '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3zM21 14v.01M14 21h.01M17.5 21H21v-3.5"/>',
    ),
    "camera": (
        "Camera (press photos)",
        '<path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/>'
        '<circle cx="12" cy="13.5" r="3.5"/>',
    ),
    "mail": ("Envelope (mailing list)", '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>'),
    "mute": ("Speaker with a cross", '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M17 9.5l4 5M21 9.5l-4 5"/>'),
    "speed": ("Speed gauge", '<path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l3.5-5.5M3 18h18"/>'),
    "lock": ("Padlock", '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
    "phone": (
        "Phone",
        '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    ),
    "ticket": (
        "Ticket",
        '<path d="M3 7a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v3a2 2 0 0 0 0 4v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a2 2 0 0 0 0-4z"/>'
        '<path d="M14 6v2M14 11v2M14 16v2"/>',
    ),
    "video": ("Video", '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10.5l5-3v9l-5-3z"/>'),
}

CHOICES = [(name, label) for name, (label, _) in ICONS.items()]


def icon_svg(name):
    """The icon as inline SVG, hidden from screen readers (its title next to it says what it means)."""
    paths = ICONS.get(name, ICONS["star"])[1]
    return format_html(
        '<svg class="c-icon__svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{}</svg>',
        mark_safe(paths),  # noqa: S308  (constant SVG markup from this module)
    )
