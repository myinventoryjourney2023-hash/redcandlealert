from config import RISK_PER_TRADE


def calculate_position(entry, sl):

    risk_per_share = abs(entry - sl)

    if risk_per_share <= 0:
        return None

    quantity = int(RISK_PER_TRADE / risk_per_share)

    target1 = entry + risk_per_share
    target2 = entry + (2 * risk_per_share)

    return {
         "sl": sl,
        "risk_per_share": round(risk_per_share, 2),
        "quantity": quantity,
        "target1": round(target1, 2),
        "target2": round(target2, 2),
    }
