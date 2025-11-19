#!/usr/bin/env python3
"""Generate a 3-minute demo video from caption slides and screenshots."""

import os
import subprocess
import re
from pathlib import Path

# Configuration
DEMO_DIR = "demo_captions"
OUTPUT_VIDEO = "demo_captions/CMMC_Scout_Demo.mp4"
TARGET_DURATION = 180  # 3 minutes in seconds
FPS = 30


def natural_sort_key(filename):
    """Natural sort key for filenames with numbers."""
    # Extract number and suffix from filename
    # e.g., "01-caption.png" -> (1, "caption")
    # e.g., "01.png" -> (1, "")
    # e.g., "13a.png" -> (13, "a")
    base = os.path.basename(filename)
    match = re.match(r'(\d+)([a-z]?)-?(caption)?\.png', base)
    if match:
        num = int(match.group(1))
        suffix = match.group(2) or ""
        is_caption = match.group(3) == "caption"
        # Caption comes before screenshot: (num, 0) vs (num, 1)
        # Then alphabetically by suffix
        return (num, 0 if is_caption else 1, suffix)
    return (999, 999, base)


def get_ordered_slides():
    """Get all PNG files in order: caption, then screenshot(s)."""
    png_files = list(Path(DEMO_DIR).glob("*.png"))

    # Sort using natural sort
    sorted_files = sorted(png_files, key=lambda x: natural_sort_key(str(x)))

    return [str(f) for f in sorted_files]


def create_video_with_ffmpeg(slides, duration_per_slide):
    """Create video using ffmpeg concat demuxer."""

    # Create a temporary file list for ffmpeg
    concat_file = os.path.join(DEMO_DIR, "filelist.txt")

    with open(concat_file, "w") as f:
        for slide in slides:
            # ffmpeg concat format: file 'path' and duration
            f.write(f"file '{os.path.basename(slide)}'\n")
            f.write(f"duration {duration_per_slide}\n")

        # Add the last file again without duration (ffmpeg requirement)
        if slides:
            f.write(f"file '{os.path.basename(slides[-1])}'\n")

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-f", "concat",
        "-safe", "0",
        "-i", "filelist.txt",
        "-pix_fmt", "yuv420p",  # Compatibility
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",  # Ensure 1920x1080
        "-c:v", "libx264",  # Video codec
        os.path.basename(OUTPUT_VIDEO)
    ]

    print(f"\n🎬 Generating video with ffmpeg...")

    # Run ffmpeg from the demo_captions directory
    result = subprocess.run(
        cmd,
        cwd=DEMO_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"\n❌ Error running ffmpeg:")
        print(result.stderr)
        return False

    # Clean up temporary file
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return True


def main():
    """Generate the demo video."""
    print("=" * 70)
    print("CMMC Scout Demo Video Generator")
    print("=" * 70)

    # Get ordered slides
    slides = get_ordered_slides()

    if not slides:
        print("❌ No slides found! Please check the demo_captions directory.")
        return

    print(f"\n✓ Found {len(slides)} slides")

    # Calculate duration per slide
    duration_per_slide = TARGET_DURATION / len(slides)

    print(f"✓ Target duration: {TARGET_DURATION} seconds (3 minutes)")
    print(f"✓ Duration per slide: {duration_per_slide:.2f} seconds")

    # List slides
    print(f"\n📋 Slide Order:")
    for i, slide in enumerate(slides, 1):
        print(f"   {i:2d}. {os.path.basename(slide)}")

    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ Error: ffmpeg not found!")
        print("   Install with: brew install ffmpeg")
        return

    # Create the video
    if create_video_with_ffmpeg(slides, duration_per_slide):
        print(f"\n✅ Video created successfully!")
        print(f"   Output: {OUTPUT_VIDEO}")

        # Get file size
        if os.path.exists(OUTPUT_VIDEO):
            size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
            print(f"   Size: {size_mb:.2f} MB")

            # Get actual duration
            duration_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                OUTPUT_VIDEO
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                actual_duration = float(result.stdout.strip())
                print(f"   Duration: {actual_duration:.1f} seconds ({actual_duration/60:.2f} minutes)")

        print(f"\n🎥 Next steps:")
        print(f"   1. Review the video: open {OUTPUT_VIDEO}")
        print(f"   2. Upload to YouTube/Vimeo for Devpost submission")
        print(f"   3. Add to README.md")
    else:
        print("\n❌ Video creation failed!")


if __name__ == "__main__":
    main()
