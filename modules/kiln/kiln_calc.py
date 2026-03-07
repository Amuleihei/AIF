# =====================================================
# 托材积计算
# 假设板规格：950 x W x 22 mm
# =====================================================

def tray_volume(spec):
    # 支持:
    # 1) 84x297
    # 2) 950x84x21x297
    # 3) 84x297+71x378
    if "+" in spec:
        return sum(tray_volume(s) for s in spec.split("+") if s)

    parts = [p for p in str(spec).split("x") if p]

    if len(parts) == 2:
        w = int(parts[0])
        n = int(parts[1])
        length = 0.95
        thick = 0.021
        width = w / 1000
        return length * width * thick * n

    if len(parts) == 4:
        l = int(parts[0]) / 1000
        w = int(parts[1]) / 1000
        t = int(parts[2]) / 1000
        n = int(parts[3])
        return l * w * t * n

    return 0.0


def total_volume(trays):

    v = 0

    for t in trays:
        v += tray_volume(t["spec"])

    return v
