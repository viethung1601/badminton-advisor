WIDTH = {"narrow": 0.0, "standard": 0.5, "wide": 1.0}
# Importance weights (a design decision, not yet validated with real users)
W_WIDTH, W_LIGHT = 2.0, 1.0
# the user picks men/women; unisex shoes are included automatically
GENDERS = {"men", "women"}

def explain(r, width, prefer_light) -> str:
    parts = [f"fit {r.width}" + (" (match)" if width and r.width == width
                                 else f" (you: {width})" if width else "")
             if isinstance(r.width, str) else "fit: no data"]
    if prefer_light:
        parts.append(
            f"weight {r.weight_g:.0f} g (measured at EU size {r.weight_ref_size_eu:g})")
    return "; ".join(parts)