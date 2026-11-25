"""외부 라이브러리 없이 꺾은선 그래프를 SVG로 그린다.

series 하나는 (이름, xs, ys, 색, 점선인가, 점을 찍는가) 튜플이다.
"""

import math

FONT = "font-family='-apple-system, Segoe UI, Noto Sans KR, sans-serif'"


def nice_step(span, target=6):
    """눈금 간격: 1, 2, 2.5, 5 × 10^k 중 눈금이 target개 안팎이 되는 것."""
    if span <= 0:
        return 1
    raw = span / target
    power = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * power:
            return m * power
    return 10 * power


def ticks(lo, hi, target=6):
    step = nice_step(hi - lo, target)
    out = []
    v = math.ceil(lo / step) * step
    while v <= hi + step * 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def fmt(v):
    if abs(v - round(v)) < 1e-9:
        return "%d" % round(v)
    return ("%.2f" % v).rstrip("0").rstrip(".")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panel(x0, y0, w, h, title, xlabel, ylabel, series, xlim, ylim, xticks=None):
    """(x0, y0)에서 시작하는 w×h 영역에 그래프 하나를 그린 SVG 조각 목록."""
    left, right, top, bottom = 58, 12, 34, 46
    px0, py0 = x0 + left, y0 + top
    pw, ph = w - left - right, h - top - bottom
    xmin, xmax = xlim
    ymin, ymax = ylim

    def sx(x):
        return px0 + (x - xmin) / (xmax - xmin) * pw

    def sy(y):
        return py0 + ph - (y - ymin) / (ymax - ymin) * ph

    out = []
    out.append("<text x='%.1f' y='%.1f' font-size='15' font-weight='600' fill='#111827' %s>%s</text>"
               % (px0, y0 + 20, FONT, esc(title)))
    # 격자와 y 눈금
    for v in ticks(ymin, ymax):
        y = sy(v)
        out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#e5e7eb'/>" % (px0, y, px0 + pw, y))
        out.append("<text x='%.1f' y='%.1f' font-size='11' fill='#4b5563' text-anchor='end' %s>%s</text>"
                   % (px0 - 6, y + 4, FONT, fmt(v)))
    # x 눈금
    for v in (xticks if xticks is not None else ticks(xmin, xmax, 8)):
        x = sx(v)
        out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#9ca3af'/>" % (x, py0 + ph, x, py0 + ph + 4))
        out.append("<text x='%.1f' y='%.1f' font-size='11' fill='#4b5563' text-anchor='middle' %s>%s</text>"
                   % (x, py0 + ph + 17, FONT, fmt(v)))
    # 축
    out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#6b7280'/>" % (px0, py0 + ph, px0 + pw, py0 + ph))
    out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#6b7280'/>" % (px0, py0, px0, py0 + ph))
    out.append("<text x='%.1f' y='%.1f' font-size='12' fill='#374151' text-anchor='middle' %s>%s</text>"
               % (px0 + pw / 2, py0 + ph + 36, FONT, esc(xlabel)))
    out.append("<text x='%.1f' y='%.1f' font-size='12' fill='#374151' text-anchor='middle' "
               "transform='rotate(-90 %.1f %.1f)' %s>%s</text>"
               % (x0 + 16, py0 + ph / 2, x0 + 16, py0 + ph / 2, FONT, esc(ylabel)))
    # 선
    out.append("<clipPath id='clip%d_%d'><rect x='%.1f' y='%.1f' width='%.1f' height='%.1f'/></clipPath>"
               % (x0, y0, px0, py0 - 2, pw, ph + 4))
    for name, xs, ys, color, dashed, markers in series:
        pts = " ".join("%.1f,%.1f" % (sx(x), sy(y)) for x, y in zip(xs, ys))
        dash = " stroke-dasharray='6 4'" if dashed else ""
        out.append("<polyline points='%s' fill='none' stroke='%s' stroke-width='2'%s clip-path='url(#clip%d_%d)'/>"
                   % (pts, color, dash, x0, y0))
        if markers:
            for x, y in zip(xs, ys):
                if ymin <= y <= ymax:
                    out.append("<circle cx='%.1f' cy='%.1f' r='3.2' fill='%s' stroke='white' stroke-width='1'/>"
                               % (sx(x), sy(y), color))
    return out


def legend(x, y, series, columns=1, col_width=230):
    out = []
    for i, (name, _xs, _ys, color, dashed, markers) in enumerate(series):
        cx = x + (i % columns) * col_width
        cy = y + (i // columns) * 20
        dash = " stroke-dasharray='6 4'" if dashed else ""
        out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' stroke-width='2'%s/>"
                   % (cx, cy, cx + 28, cy, color, dash))
        if markers:
            out.append("<circle cx='%.1f' cy='%.1f' r='3.2' fill='%s'/>" % (cx + 14, cy, color))
        out.append("<text x='%.1f' y='%.1f' font-size='12' fill='#111827' %s>%s</text>"
                   % (cx + 36, cy + 4, FONT, esc(name)))
    return out


def save(path, width, height, parts):
    with open(path, "w", encoding="utf-8") as f:
        f.write("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>\n"
                % (width, height, width, height))
        f.write("<rect width='100%' height='100%' fill='white'/>\n")
        for p in parts:
            f.write(p + "\n")
        f.write("</svg>\n")
