# news-image-20261122 — "The World in One Day"
# A program that draws one 1024x1024 newspaper front page summing up
# Sunday 22 November 2026's world news. Pure Python 3.13 stdlib only:
# no network, no files read, no randomness, no wall-clock time.
# The picture is fully deterministic: two runs write identical bytes.
#
# Layout (1024 x 1024, editorial front page):
#   masthead  -> "THE WORLD IN ONE DAY" + date
#   lead      -> Gulf crisis: Iran strikes a US base in Kuwait,
#                tankers burn off Oman (big headline + drawn sea scene)
#   four cards -> COP31 deadlock / Peru quake / Ukraine barrage /
#                Shenzhen summit (Trump, Xi, Putin at APEC)
#   footer    -> date line + make.fun credit
#
# Text is rendered with a small 5x7 bitmap font defined below, scaled
# up. The PNG is encoded by hand (zlib + struct), RGB, no filters.

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER   = (247, 243, 234)   # warm newsprint
INK     = (18, 24, 33)      # near-black text
NAVY    = (14, 42, 71)      # masthead / footer band
GOLD    = (201, 162, 39)    # rules and accents
RED     = (178, 34, 34)     # lead kicker / urgency
ORANGE  = (232, 116, 28)    # explosion
YELLOW  = (245, 196, 66)    # flame core
TEAL    = (15, 118, 110)    # Peru card
SLATE   = (71, 85, 105)     # Ukraine card
PURPLE  = (88, 60, 144)     # summit card
SEA     = (23, 58, 94)      # lead scene sea
SKY     = (214, 124, 62)    # lead scene dusk sky
SMOKE   = (120, 124, 130)
WHITE   = (255, 255, 255)
CARD    = (255, 255, 255)
MUTED   = (90, 96, 104)     # summary grey

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 cells, '1' = ink, '0' = empty. Uppercase only;
# all copy in this image is set in capitals, as a newspaper would set it.
FONT = {
    'A': ("01110","10001","10001","11111","10001","10001","10001"),
    'B': ("11110","10001","10001","11110","10001","10001","11110"),
    'C': ("01110","10001","10000","10000","10000","10001","01110"),
    'D': ("11110","10001","10001","10001","10001","10001","11110"),
    'E': ("11111","10000","10000","11110","10000","10000","11111"),
    'F': ("11111","10000","10000","11110","10000","10000","10000"),
    'G': ("01110","10001","10000","10111","10001","10001","01111"),
    'H': ("10001","10001","10001","11111","10001","10001","10001"),
    'I': ("01110","00100","00100","00100","00100","00100","01110"),
    'J': ("00111","00010","00010","00010","00010","10010","01100"),
    'K': ("10001","10010","10100","11000","10100","10010","10001"),
    'L': ("10000","10000","10000","10000","10000","10000","11111"),
    'M': ("10001","11011","10101","10101","10001","10001","10001"),
    'N': ("10001","11001","10101","10011","10001","10001","10001"),
    'O': ("01110","10001","10001","10001","10001","10001","01110"),
    'P': ("11110","10001","10001","11110","10000","10000","10000"),
    'Q': ("01110","10001","10001","10001","10101","10010","01101"),
    'R': ("11110","10001","10001","11110","10100","10010","10001"),
    'S': ("01111","10000","10000","01110","00001","00001","11110"),
    'T': ("11111","00100","00100","00100","00100","00100","00100"),
    'U': ("10001","10001","10001","10001","10001","10001","01110"),
    'V': ("10001","10001","10001","10001","10001","01010","00100"),
    'W': ("10001","10001","10001","10101","10101","11011","10001"),
    'X': ("10001","10001","01010","00100","01010","10001","10001"),
    'Y': ("10001","10001","01010","00100","00100","00100","00100"),
    'Z': ("11111","00001","00010","00100","01000","10000","11111"),
    '0': ("01110","10001","10011","10101","11001","10001","01110"),
    '1': ("00100","01100","00100","00100","00100","00100","01110"),
    '2': ("01110","10001","00001","00110","01000","10000","11111"),
    '3': ("11111","00010","00100","00010","00001","10001","01110"),
    '4': ("00010","00110","01010","10010","11111","00010","00010"),
    '5': ("11111","10000","11110","00001","00001","10001","01110"),
    '6': ("00110","01000","10000","11110","10001","10001","01110"),
    '7': ("11111","00001","00010","00100","01000","01000","01000"),
    '8': ("01110","10001","10001","01110","10001","10001","01110"),
    '9': ("01110","10001","10001","01111","00001","00010","01100"),
    ' ': ("00000","00000","00000","00000","00000","00000","00000"),
    '.': ("00000","00000","00000","00000","00000","01100","01100"),
    ',': ("00000","00000","00000","00000","01100","00100","01000"),
    "'": ("00100","00100","01000","00000","00000","00000","00000"),
    ':': ("00000","01100","01100","00000","01100","01100","00000"),
    '-': ("00000","00000","00000","01110","00000","00000","00000"),
    '!': ("00100","00100","00100","00100","00100","00000","00100"),
    '?': ("01110","10001","00001","00110","00100","00000","00100"),
    '&': ("01100","10010","10100","01000","10101","10010","01101"),
    '/': ("00001","00010","00010","00100","01000","01000","10000"),
    '(': ("00010","00100","01000","01000","01000","00100","00010"),
    ')': ("01000","00100","00010","00010","00010","00100","01000"),
    '%': ("11001","11010","00010","00100","01000","01011","10011"),
    '+': ("00000","00100","00100","11111","00100","00100","00000"),
    '=': ("00000","00000","11111","00000","11111","00000","00000"),
    '"': ("01010","01010","00000","00000","00000","00000","00000"),
    '|': ("00100","00100","00100","00100","00100","00100","00100"),
}


def glyph_rows(ch):
    return FONT.get(ch, FONT['?'])


def text_width(text, scale):
    # one cell per glyph column plus one blank column between glyphs
    return len(text) * 6 * scale - scale


def wrap_text(text, max_width, scale):
    words = text.split(' ')
    lines = []
    current = ''
    for word in words:
        trial = word if not current else current + ' ' + word
        if text_width(trial, scale) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            row = bytes(color) * (x1 - x0)
            self.px[base:base + (x1 - x0) * 3] = row

    def rect(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = max(1, thick // 2)
        while True:
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    if ox * ox + oy * oy <= r * r + r:
                        self.set(x0 + ox, y0 + oy, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            span = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - span, yy, span * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=2):
        self.disc(cx, cy, r, color)
        self.disc(cx, cy, r - thick, PAPER)

    def fill_polygon(self, points, color):
        # even-odd scanline fill; points is a list of (x, y)
        ys = [p[1] for p in points]
        for yy in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    t = (yy - y0) / (y1 - y0)
                    xs.append(int(x0 + t * (x1 - x0)))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.fill_rect(xs[j], yy, xs[j + 1] - xs[j] + 1, 1, color)

    def starburst(self, cx, cy, r_outer, r_inner, spikes, color):
        import math
        pts = []
        for i in range(spikes * 2):
            ang = math.pi * i / spikes - math.pi / 2
            r = r_outer if i % 2 == 0 else r_inner
            pts.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
        self.fill_polygon(pts, color)

    def draw_text(self, x, y, text, scale, color, align='left'):
        text = text.upper()
        if align == 'center':
            x -= text_width(text, scale) // 2
        elif align == 'right':
            x -= text_width(text, scale)
        cx = x
        for ch in text:
            rows = glyph_rows(ch)
            for gy in range(7):
                row = rows[gy]
                for gx in range(5):
                    if row[gx] == '1':
                        self.fill_rect(cx + gx * scale, y + gy * scale,
                                       scale, scale, color)
            cx += 6 * scale
        return y + 7 * scale

    def draw_lines(self, x, y, lines, scale, color, leading=None, align='left'):
        if leading is None:
            leading = 7 * scale + 4
        for line in lines:
            self.draw_text(x, y, line, scale, color, align=align)
            y += leading
        return y


# ---------------------------------------------------------------- PNG writer
def encode_png(canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for yy in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[yy * stride:(yy + 1) * stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack('>I', len(data)) + tag + data
        out += struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack('>IIBBBBB', canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', compressed) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- scenes
def draw_masthead(cv):
    cv.fill_rect(0, 0, W, 140, NAVY)
    cv.fill_rect(0, 140, W, 4, GOLD)
    cv.draw_text(W // 2, 26, "THE WORLD IN ONE DAY", 5, WHITE, align='center')
    cv.draw_text(W // 2, 82, "SUNDAY  |  22 NOVEMBER 2026", 3, GOLD, align='center')
    cv.draw_text(W // 2, 116, "FIVE STORIES FROM AROUND THE GLOBE", 2, (176, 196, 214),
                 align='center')


def draw_lead_scene(cv, x, y, w, h):
    # dusk sky over a dark sea, a tanker, two explosions, drifting smoke
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_rect(x, y, w, h // 2, SKY)
    cv.fill_rect(x, y + h // 2, w, h - h // 2, SEA)
    horizon = y + h // 2
    cv.fill_rect(x, horizon, w, 3, GOLD)
    # sun low on the horizon: orange halo, yellow core
    cv.disc(x + w - 70, horizon - 26, 26, ORANGE)
    cv.disc(x + w - 70, horizon - 26, 18, YELLOW)
    # tanker: hull + stacked containers
    hx, hy = x + 24, horizon + 42
    cv.fill_polygon([(hx, hy), (hx + 220, hy), (hx + 196, hy + 34),
                     (hx + 12, hy + 34)], (28, 34, 44))
    cv.fill_rect(hx + 26, hy - 30, 44, 30, RED)
    cv.fill_rect(hx + 76, hy - 30, 44, 30, GOLD)
    cv.fill_rect(hx + 126, hy - 30, 44, 30, TEAL)
    cv.fill_rect(hx + 176, hy - 22, 26, 22, WHITE)
    # explosion bursts above the ship
    cv.starburst(x + 70, y + 58, 46, 20, 9, ORANGE)
    cv.starburst(x + 70, y + 58, 26, 12, 9, YELLOW)
    cv.starburst(x + w - 96, y + 92, 34, 15, 8, ORANGE)
    cv.starburst(x + w - 96, y + 92, 18, 8, 8, YELLOW)
    # smoke puffs
    for sx, sy, sr in ((x + 118, y + 34, 16), (x + 148, y + 18, 12),
                       (x + w - 60, y + 66, 13), (x + w - 34, y + 50, 10)):
        cv.disc(sx, sy, sr, SMOKE)
    # missile arcs streaking down
    cv.line(x + 150, y + 6, x + 96, y + 52, WHITE, 2)
    cv.line(x + 210, y + 2, x + 168, y + 44, WHITE, 2)
    # sea glints
    for gx in range(x + 12, x + w - 12, 46):
        cv.fill_rect(gx, horizon + 66, 26, 3, (64, 110, 150))


def draw_globe(cv, cx, cy, r, color):
    cv.ring(cx, cy, r, color, 4)
    cv.line(cx - r, cy, cx + r, cy, color, 2)
    cv.line(cx, cy - r, cx, cy + r, color, 2)
    # meridians: two offset vertical arcs faked with short lines
    for dx in (-r // 2, r // 2):
        cv.line(cx + dx, cy - r + 8, cx + dx, cy + r - 8, color, 2)


def draw_flame(cv, cx, cy, size, color):
    cv.fill_polygon([
        (cx, cy - size), (cx + size // 2, cy - size // 4),
        (cx + size // 3, cy + size // 2), (cx - size // 3, cy + size // 2),
        (cx - size // 2, cy - size // 4)], color)
    cv.fill_polygon([
        (cx, cy - size // 3), (cx + size // 5, cy + size // 6),
        (cx - size // 5, cy + size // 6)], YELLOW)


def draw_quake(cv, cx, cy, w, color):
    pts = [(cx - w // 2, cy), (cx - w // 3, cy - 26), (cx - w // 6, cy + 18),
           (cx, cy - 34), (cx + w // 6, cy + 14), (cx + w // 3, cy - 22),
           (cx + w // 2, cy)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, 4)
    cv.line(cx - w // 2, cy + 34, cx + w // 2, cy + 34, color, 3)


def draw_drone(cv, cx, cy, color):
    cv.fill_rect(cx - 16, cy - 8, 32, 16, color)
    cv.disc(cx - 22, cy - 16, 10, color)
    cv.disc(cx + 22, cy - 16, 10, color)
    cv.disc(cx - 22, cy + 16, 10, color)
    cv.disc(cx + 22, cy + 16, 10, color)
    cv.line(cx - 16, cy - 12, cx - 22, cy - 16, color, 3)
    cv.line(cx + 16, cy - 12, cx + 22, cy - 16, color, 3)
    cv.line(cx - 16, cy + 12, cx - 22, cy + 16, color, 3)
    cv.line(cx + 16, cy + 12, cx + 22, cy + 16, color, 3)


def draw_flags(cv, cx, cy, color):
    # three small flags on poles: a trilateral handshake of summits
    for i, c in enumerate((RED, GOLD, TEAL)):
        px = cx - 44 + i * 44
        cv.line(px, cy - 34, px, cy + 30, color, 3)
        cv.fill_rect(px, cy - 34, 34, 22, c)
    cv.line(cx - 52, cy + 30, cx + 52, cy + 30, color, 3)


PICTOGRAMS = {
    'cop': lambda cv, cx, cy: (draw_globe(cv, cx, cy - 6, 34, TEAL),
                               draw_flame(cv, cx + 26, cy + 22, 26, ORANGE)),
    'quake': lambda cv, cx, cy: draw_quake(cv, cx, cy, 84, RED),
    'drone': lambda cv, cx, cy: (draw_drone(cv, cx, cy - 4, SLATE),
                                 cv.starburst(cx + 30, cy + 26, 16, 7, 7, ORANGE)),
    'flags': lambda cv, cx, cy: draw_flags(cv, cx, cy, PURPLE),
}


def draw_card(cv, x, y, w, h, accent, tag, headline, summary, picto):
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, (214, 206, 188), 2)
    cv.fill_rect(x, y, w, 8, accent)
    px = x + 74
    py = y + h // 2 + 6
    PICTOGRAMS[picto](cv, px, py)
    tx = x + 150
    tw = w - 150 - 20
    yy = y + 26
    yy = cv.draw_text(tx, yy, tag, 2, accent)
    yy += 8
    head_lines = wrap_text(headline, tw, 3)
    yy = cv.draw_lines(tx, yy, head_lines, 3, INK)
    yy += 6
    sum_lines = wrap_text(summary, tw, 2)
    cv.draw_lines(tx, yy, sum_lines, 2, MUTED)


def draw_footer(cv):
    cv.fill_rect(0, 952, W, 72, NAVY)
    cv.fill_rect(0, 952, W, 4, GOLD)
    cv.draw_text(W // 2, 972, "SUNDAY 22 NOVEMBER 2026  |  FIVE STORIES  |  ONE DAY",
                 2, WHITE, align='center')
    cv.draw_text(W // 2, 998, "DRAWN BY AN AI AGENT FOR MAKE.FUN",
                 2, GOLD, align='center')


# ---------------------------------------------------------------- build
def build_image():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)

    # ---- lead story: Gulf crisis
    ly = 164
    cv.draw_text(32, ly, "GULF ON EDGE", 3, RED)
    headline = "IRAN STRIKES US BASE IN KUWAIT AS TANKERS BURN OFF OMAN"
    lines = wrap_text(headline, 560, 4)
    yy = cv.draw_lines(32, ly + 34, lines, 4, INK)
    summary = ("Tehran hits a US air base and Gulf shipping as tensions "
               "spiral. Washington warns of threats ahead of Thanksgiving.")
    yy = cv.draw_lines(32, yy + 10, wrap_text(summary, 560, 2), 2, MUTED)
    draw_lead_scene(cv, 624, ly, 368, 300)

    cv.fill_rect(32, 486, W - 64, 3, GOLD)

    # ---- four story cards, 2 x 2
    cards = [
        (TEAL, "COP31  |  CLIMATE", "COP31 DEADLOCK",
         "Fossil-fuel fight stalls the climate talks in overtime.",
         "Negotiators deadlocked as the summit runs past deadline.", 'cop'),
        (RED, "PERU  |  EARTHQUAKE", "PERU QUAKE",
         "Magnitude 6.9 shakes the Andes.",
         "Tremor felt in Lima. No casualties reported so far.", 'quake'),
        (SLATE, "UKRAINE  |  WAR", "UKRAINE UNDER FIRE",
         "Russia fires 400 drones and 110 missiles.",
         "One of the war's biggest barrages. A Baltic cargo ship is hit.",
         'drone'),
        (PURPLE, "SHENZHEN  |  SUMMIT", "SHENZHEN SUMMIT",
         "Trump, Xi and Putin meet at APEC.",
         "Leaders tout a momentous trilateral as chip exports stir debate.",
         'flags'),
    ]
    cw = (W - 64 - 16) // 2
    ch = 208
    positions = [(32, 508), (32 + cw + 16, 508),
                 (32, 508 + ch + 16), (32 + cw + 16, 508 + ch + 16)]
    for (accent, tag, headline, dek, summary, picto), (cx, cy) in zip(cards, positions):
        draw_card(cv, cx, cy, cw, ch, accent, tag, headline,
                  dek + " " + summary, picto)

    draw_footer(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = encode_png(build_image())
    with open(path, "wb") as f:
        f.write(data)
    print("wrote", path, len(data), "bytes")


if __name__ == "__main__":
    main()
