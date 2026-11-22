"""Reference mockup for the weather band of the "today" dashboard.

This is a standalone drawing sketch, not part of the runtime. It shows the
intended look: a condition icon before the temperature, the temperature 3 hours
later in parentheses, a wind symbol with speed, and a rain drop with the chance
and hour (hidden when the chance is below the threshold). The icon drawing
helpers (sun, cloud, partly cloudy, wind, drop) use only Pillow primitives and
can be reused or adapted for the dashlib icon set. Run it with
    python docs/reference/weather_band_mockup.py
It writes mockup.png in the current folder. Font paths are DejaVu on Linux.
"""
from PIL import Image, ImageDraw, ImageFont
import math

W = 758
S = 2  # draw at 2x then downscale for smooth edges
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def f(path, px): return ImageFont.truetype(path, px * S)

def sun(d, cx, cy, r, w):
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=0, width=w)
    for i in range(8):
        a = i * math.pi / 4
        d.line([cx+math.cos(a)*(r+6*S), cy+math.sin(a)*(r+6*S), cx+math.cos(a)*(r+16*S), cy+math.sin(a)*(r+16*S)], fill=0, width=w)

def cloud(d, cx, cy, s, w, fill=255):
    # s = overall scale (half width)
    parts = [(-0.45, 0.15, 0.38), (0.0, -0.1, 0.5), (0.5, 0.15, 0.36)]
    # outline: draw filled black circles bigger, then filled white circles smaller
    for ox, oy, r in parts:
        d.ellipse([cx+ox*s-r*s, cy+oy*s-r*s, cx+ox*s+r*s, cy+oy*s+r*s], fill=0)
    d.rectangle([cx-0.45*s, cy+0.1*s, cx+0.5*s, cy+0.51*s], fill=0)
    for ox, oy, r in parts:
        rr = r*s - w
        d.ellipse([cx+ox*s-rr, cy+oy*s-rr, cx+ox*s+rr, cy+oy*s+rr], fill=255)
    d.rectangle([cx-0.45*s, cy+0.1*s, cx+0.5*s, cy+0.51*s-w], fill=255)
    d.line([cx-0.45*s, cy+0.51*s-w/2, cx+0.5*s, cy+0.51*s-w/2], fill=0, width=w)

def partly(d, cx, cy, s, w):
    sun(d, cx+0.35*s, cy-0.45*s, int(0.28*s), w)
    cloud(d, cx-0.05*s, cy+0.15*s, s*0.8, w)

def wind(d, x, y, w):
    # three wavy lines with a curl on the end
    for i, (dy, length) in enumerate([(-16*S, 54*S), (0, 66*S), (16*S, 44*S)]):
        yy = y + dy
        d.line([x, yy, x+length, yy], fill=0, width=w)
        r = 8*S
        if i == 0:
            d.arc([x+length-r, yy-2*r, x+length+r, yy], 270, 90+360-0, fill=0, width=w) if False else d.arc([x+length-r, yy-2*r, x+length+r, yy], -90, 150, fill=0, width=w)
        elif i == 1:
            d.arc([x+length-r, yy-2*r, x+length+r, yy], -90, 150, fill=0, width=w)
        else:
            d.arc([x+length-r, yy, x+length+r, yy+2*r], -150, 90, fill=0, width=w)

def drop(d, cx, cy, r, w):
    d.polygon([(cx, cy-2.1*r), (cx-r*0.95, cy+0.1*r), (cx+r*0.95, cy+0.1*r)], fill=0)
    d.ellipse([cx-r, cy-r*0.1, cx+r, cy+r*1.9], fill=0)

def band(rain=True, date="Sat Nov 21"):
    H = 270
    img = Image.new("L", (W*S, H*S), 255)
    d = ImageDraw.Draw(img)
    d.text((32*S, 14*S), date, font=f(FB, 56), fill=0)
    y0 = 110
    # rule
    d.line([32*S, (y0-8)*S, (W-32)*S, (y0-8)*S], fill=0, width=3*S)
    # temperature block: icon, big temp, parenthesis temp
    cloud(d, 82*S, (y0+62)*S, 52*S, 6*S)
    d.text((142*S, (y0+10)*S), "7°", font=f(FB, 92), fill=0)
    d.text((142*S + d.textlength("7°", font=f(FB, 92)) + 8*S, (y0+40)*S), "(5°)", font=f(FR, 52), fill=0)
    # wind block
    wx = 385 if rain else 440
    wind(d, wx*S, (y0+58)*S, 5*S)
    d.text(((wx+84)*S, (y0+24)*S), "18", font=f(FB, 56), fill=0)
    d.text(((wx+84)*S, (y0+84)*S), "km/h", font=f(FR, 26), fill=0)
    # rain block
    if rain:
        rx = 580
        drop(d, (rx+12)*S, (y0+42)*S, 14*S, 3*S)
        d.text(((rx+36)*S, (y0+18)*S), "40%", font=f(FB, 46), fill=0)
        d.text(((rx+36)*S, (y0+72)*S), "by 3 pm", font=f(FR, 24), fill=0)
    return img.resize((W, H), Image.LANCZOS)

a = band(True)
b = band(False, "Sun Nov 22")
canvas = Image.new("L", (W, a.height + b.height + 30), 255)
canvas.paste(a, (0, 0))
ImageDraw.Draw(canvas).line([0, a.height+14, W, a.height+14], fill=160, width=1)
canvas.paste(b, (0, a.height + 30))
canvas.save("mockup.png")
print(canvas.size)
