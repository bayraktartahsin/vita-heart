#!/usr/bin/env python3
"""Draw docs/architecture.png with Pillow. No design tool, reproducible, diffable."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
W, H = 1800, 1100
BG, PANEL, TEXT, DIM, WARM, HEART, CALM, LINE = "#0F1216", "#1A1F26", "#F4F1EA", "#B8B3A8", "#F2A93B", "#E8635A", "#7FB77E", "#3A4450"


def font(size, bold=False):
    for p in (f"/System/Library/Fonts/Supplemental/Arial{' Bold' if bold else ''}.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def box(d, x, y, w, h, title, lines, accent=WARM):
    d.rounded_rectangle((x, y, x + w, y + h), 22, fill=PANEL, outline=LINE, width=2)
    d.rectangle((x, y + 12, x + 8, y + h - 12), fill=accent)
    d.text((x + 26, y + 18), title, fill=TEXT, font=font(30, True))
    for i, ln in enumerate(lines):
        d.text((x + 26, y + 66 + i * 32), ln, fill=DIM, font=font(24))


def arrow(d, a, b, label="", color=DIM):
    d.line([a, b], fill=color, width=4)
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / n, dy / n
    tip = b
    d.polygon([tip, (tip[0] - 16 * ux + 8 * uy, tip[1] - 16 * uy - 8 * ux), (tip[0] - 16 * ux - 8 * uy, tip[1] - 16 * uy + 8 * ux)], fill=color)
    if label:
        d.text(((a[0] + b[0]) / 2 + 10, (a[1] + b[1]) / 2 - 30), label, fill=color, font=font(22))


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Vita Heart", fill=WARM, font=font(48, True))
    d.text((300, 52), "the television an older parent already watches becomes their health room", fill=DIM, font=font(26))

    box(d, 60, 130, 520, 260, "Fire TV · Vega OS", ["React Native 0.83, TVFocusGuideView", "Morning Board · Medication Moment", "Clock setup · Heart Session · Family", "long-poll /events, D-pad + OK only"], WARM)
    box(d, 60, 430, 520, 200, "Apple Watch", ["standalone watchOS app", "HKWorkoutSession live heart rate", "POST /session/hr every ~5 s"], HEART)
    box(d, 60, 670, 520, 200, "Ring (front door, hall)", ["doorbell · contact · temperature · air", "webhooks, X-Signature HMAC-SHA256", "Playground sandbox / signed simulator"], CALM)

    box(d, 700, 130, 640, 340, "Vita Heart API · Lambda + API Gateway", ["FastAPI via Mangum, one deploy script", "DynamoDB `vitaheart` (single table, TTL)", "S3 photos (private, 30-day expiry)", "/board /meds /doses /session /events", "/ring/webhook  /night/run  /family  /cabinet", "/mcp (2025-11-25) + /oauth PKCE + /alexa-sim"], WARM)
    box(d, 700, 510, 640, 300, "Strands fleet · Bedrock AgentCore Runtime", ["Reader (Nova Lite vision, transcript-grounded)", "Identifier: name bridge + RxNorm", "Watchman: openFDA live recalls, lots kept", "Scribe: facts only, holds no tools", "Coach: one line per block", "every tool call traced to DynamoDB"], HEART)
    box(d, 700, 850, 640, 190, "Night Watch · EventBridge 21:00 → SNS", ["door at night · quiet morning · cold indoors", "doses · session · check-in", "one calm paragraph, banned words enforced"], CALM)

    box(d, 1420, 130, 320, 220, "Family phone", ["/family: summary, replies", "/cabinet: photograph boxes", "email from SNS"], CALM)
    box(d, 1420, 400, 320, 260, "Alexa+", ["MCP server, Streamable HTTP", "OAuth 2.1 PKCE, bare 401", "5 tools + board card", "simulated surface: browser voice,", "Bedrock picks the tool"], WARM)
    box(d, 1420, 710, 320, 200, "Sources", ["RxNorm (NIH)", "openFDA enforcement", "Amazon Bedrock models"], DIM)

    # Arrows live in the gutters; labels sit in the gutters too, never over box text.
    def gutter_label(x, y, text, color=DIM):
        for i, ln in enumerate(text.split("\n")):
            d.text((x, y + i * 22), ln, fill=color, font=font(18))

    arrow(d, (580, 250), (700, 250))
    arrow(d, (700, 300), (580, 300))
    gutter_label(596, 258, "JSON")
    gutter_label(596, 306, "events")
    arrow(d, (580, 530), (700, 420))
    gutter_label(596, 545, "heart\nrate", HEART)
    arrow(d, (580, 770), (700, 450))
    gutter_label(596, 690, "signed\nwebhooks", CALM)
    arrow(d, (1020, 470), (1020, 510))
    gutter_label(1035, 478, "read · coach · summary")
    arrow(d, (1020, 810), (1020, 850))
    arrow(d, (1340, 240), (1420, 240))
    arrow(d, (1340, 300), (1420, 300))
    arrow(d, (1420, 470), (1340, 400))
    gutter_label(1348, 470, "MCP\ntools", WARM)
    arrow(d, (1340, 700), (1420, 780))
    gutter_label(1348, 655, "NIH\nFDA")
    d.text((60, 1040), "Nothing synthetic is shown as live: heart rate carries its source; simulated Ring events are labelled; the Alexa+ surface is the sanctioned simulation over a real MCP server.", fill=DIM, font=font(22))
    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT)
    print(OUT, img.size)


if __name__ == "__main__":
    main()
