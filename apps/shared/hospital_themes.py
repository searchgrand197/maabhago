from typing import Dict, Any, Optional


def get_hospital_theme(slug: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple placeholder for hospital-specific theming of the API console.

    The current implementation ignores ``slug`` and returns a single global theme,
    but the signature matches callers that pass a hospital slug.
    """
    return {
        "bg": "#020617",
        "panel": "#020617",
        "panel_border": "#1e293b",
        "accent": "#3b82f6",
        "accent_dim": "#2563eb",
        "text": "#e5e7eb",
        "muted": "#9ca3af",
        "success": "#22c55e",
        "radius": "10px",
        "font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "swagger_bg": "#020617",
    }

