#!/usr/bin/env python3
"""Generate caption slides for demo video."""

from PIL import Image, ImageDraw, ImageFont
import os

# Slide dimensions (1920x1080 for HD video)
WIDTH = 1920
HEIGHT = 1080

# Colors
BG_COLOR = (26, 27, 38)  # Dark background
TEXT_COLOR = (255, 255, 255)  # White text
ACCENT_COLOR = (139, 92, 246)  # Purple accent

# Caption data
CAPTIONS = [
    {
        "title": "CMMC Scout",
        "subtitle": "AI-Powered Compliance Assessment",
        "description": "Using 5 vendor technologies to automate CMMC Level 2 assessments"
    },
    {
        "title": "Auth0 Authentication",
        "subtitle": "Enterprise OAuth 2.0",
        "description": "Browser-based login with authorization code flow and CSRF protection"
    },
    {
        "title": "User Authenticated",
        "subtitle": "Multi-Tenant Access",
        "description": "User profile stored in PostgreSQL database for organization management"
    },
    {
        "title": "Akka Actors Started",
        "subtitle": "Stateful Session Management",
        "description": "SessionActor, DomainActor, and ScoringActor initialized using Pykka"
    },
    {
        "title": "Anthropic Claude Haiku",
        "subtitle": "AI-Generated Assessment Questions",
        "description": "Real LLM generates unique, contextual questions for each NIST 800-171 control"
    },
    {
        "title": "Intelligent Classification",
        "subtitle": "AI-Powered Compliance Scoring",
        "description": "Claude Haiku classifies responses: Compliant, Partial, or Non-Compliant"
    },
    {
        "title": "Redpanda Event Streaming",
        "subtitle": "Real-Time Compliance Audit Trail",
        "description": "Kafka-compatible events: assessment.started, control.evaluated, gap.identified"
    },
    {
        "title": "Comet ML Tracking",
        "subtitle": "LLM Observability",
        "description": "Every AI decision logged with prompts, metrics, and confidence scores"
    },
    {
        "title": "Compliance Score Calculated",
        "subtitle": "ScoringActor Results",
        "description": "37.5% compliance (1 compliant, 1 partial, 2 non-compliant) - Red traffic light status"
    },
    {
        "title": "Gap Report Generated",
        "subtitle": "Actionable Remediation",
        "description": "Detailed recommendations for non-compliant controls with implementation steps"
    },
    {
        "title": "Comet ML Dashboard",
        "subtitle": "Full LLM Decision Audit",
        "description": "All prompts, responses, and metrics available for compliance review"
    },
    {
        "title": "Redpanda Audit Trail",
        "subtitle": "Complete Event History",
        "description": "SIEM-ready event stream for compliance reporting and security monitoring"
    },
    {
        "title": "5 Vendor Integrations",
        "subtitle": "Production-Ready Architecture",
        "description": "Auth0 + Anthropic + Comet ML + Redpanda + Akka"
    },
]


def create_caption_slide(caption_data, slide_number):
    """Create a caption slide image."""
    # Create image
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 50)
        desc_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()

    # Draw title (centered, near top)
    title = caption_data["title"]
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (WIDTH - title_width) // 2
    draw.text((title_x, 250), title, fill=ACCENT_COLOR, font=title_font)

    # Draw subtitle (centered, below title)
    subtitle = caption_data["subtitle"]
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (WIDTH - subtitle_width) // 2
    draw.text((subtitle_x, 380), subtitle, fill=TEXT_COLOR, font=subtitle_font)

    # Draw description (centered, below subtitle)
    description = caption_data["description"]
    desc_bbox = draw.textbbox((0, 0), description, font=desc_font)
    desc_width = desc_bbox[2] - desc_bbox[0]
    desc_x = (WIDTH - desc_width) // 2
    draw.text((desc_x, 500), description, fill=(200, 200, 200), font=desc_font)

    # Draw slide number (bottom right)
    slide_text = f"{slide_number:02d}"
    draw.text((WIDTH - 100, HEIGHT - 80), slide_text, fill=(100, 100, 100), font=subtitle_font)

    return img


def main():
    """Generate all caption slides."""
    output_dir = "demo_captions"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating {len(CAPTIONS)} caption slides...")

    for i, caption in enumerate(CAPTIONS, start=1):
        filename = f"{output_dir}/{i:02d}-caption.png"
        img = create_caption_slide(caption, i)
        img.save(filename)
        print(f"  Created: {filename}")

    print(f"\n✓ All slides saved to {output_dir}/")
    print(f"\nNext steps:")
    print(f"1. Take screenshots during demo and save as: 01-welcome.png, 02-auth0-login.png, etc.")
    print(f"2. Open Keynote → New Presentation → Photo Album")
    print(f"3. Alternate between caption slides and screenshots:")
    print(f"   - 01-caption.png, 01-welcome.png")
    print(f"   - 02-caption.png, 02-auth0-login.png")
    print(f"   - etc.")
    print(f"4. File → Export To → Movie (1080p, 3 seconds per slide)")


if __name__ == "__main__":
    main()
