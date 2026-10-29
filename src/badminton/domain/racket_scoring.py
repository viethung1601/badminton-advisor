import numpy as np
from sklearn.metrics.pairwise import manhattan_distances

# Natural order -> number in [0, 1]
LEVEL = {"beginner": 0.0, "intermediate": 0.5, "advanced": 1.0}
STIFFNESS = {"flexible": 0.0, "medium": 0.5, "stiff": 1.0}
BALANCE = {"head_light": 0.0, "even": 0.5, "head_heavy": 1.0}
STYLES = ["attack", "speed", "control", "allround"]  # no natural order -> one-hot

# How much each criterion matters (tunable, this is your "design decision")
W_LEVEL, W_STYLE, W_BALANCE, W_STIFF = 2.0, 2.0, 1.0, 1.0

# Rackets with a score below this threshold are dropped from the results (also a design decision, tune it after looking at real data).
# Note: the score is relative to the criteria the user filled in, so a profile with few criteria
# is penalized more heavily for "one thing wrong" than a profile with all 4 criteria.
MIN_SCORE = 0.5
EXACT = 0.999  # score >= EXACT counts as a full match

def encode(level, play_style, balance, stiffness) -> np.ndarray:
    """One racket (or one profile) -> vector: [level, balance, stiffness, 4 one-hot style columns]."""
    onehot = [1.0 if play_style == s else 0.0 for s in STYLES]
    return np.array(
        [
            LEVEL[level],
            BALANCE[balance] if balance else 0.0,
            STIFFNESS[stiffness] if stiffness else 0.0,
            *onehot,
        ]
    )


def column_weights(balance, stiffness) -> np.ndarray:
    """A column the user doesn't care about (None) gets weight = 0."""
    # a wrong one-hot style throws off 2 columns -> halve the weight so a "wrong style" costs exactly W_STYLE
    return np.array(
        [
            W_LEVEL,
            W_BALANCE if balance else 0.0,
            W_STIFF if stiffness else 0.0,
            *[W_STYLE / 2] * len(STYLES),
        ]
    )

def score_rackets(df, level, play_style, balance, stiffness):
    """Add a score column to df (same formula as before, split out for reuse)."""
    X = np.vstack(
        [encode(r.level, r.play_style, r.balance, r.stiffness) for r in df.itertuples()]
    )
    user = encode(level, play_style, balance, stiffness).reshape(1, -1)
    w = column_weights(balance, stiffness)
    dist = manhattan_distances(X * w, user * w).ravel()
    df = df.copy()
    df["score"] = 1 - dist / max_possible(w)
    return df

def max_possible(w: np.ndarray) -> float:
    """The largest possible distance -> used to normalize the score to [0, 1].
    level/balance/stiffness off by at most 1 * w; a wrong style = 2 columns off * (W_STYLE/2) = W_STYLE."""
    return w[0] + w[1] + w[2] + 2 * w[3]  # w[3] = W_STYLE/2; a wrong style throws off 2 columns


def explain(r, level, play_style, balance, stiffness) -> str:
    parts = []
    parts.append(f"level {r.level}" + (" (match)" if r.level == level else f" (you: {level})"))
    parts.append(f"style {r.play_style}" + (" (match)" if r.play_style == play_style else f" (you: {play_style})"))
    if balance:
        parts.append(f"balance {r.balance}" + (" (match)" if r.balance == balance else f" (you: {balance})"))
    if stiffness:
        parts.append(f"stiffness {r.stiffness}" + (" (match)" if r.stiffness == stiffness else f" (you: {stiffness})"))
    return "; ".join(parts)