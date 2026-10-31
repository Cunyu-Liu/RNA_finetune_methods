#!/usr/bin/env python3
import sys
import zipfile
from pathlib import Path

from pptx import Presentation


def validate(path):
    prs = Presentation(str(path))
    issues = []
    for index, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.left < -1000 or shape.top < -1000 or \
                    shape.left + shape.width > prs.slide_width + 1000 or \
                    shape.top + shape.height > prs.slide_height + 1000:
                issues.append((index, "out_of_bounds", shape.name))
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                if not paragraph.text.strip():
                    continue
                if paragraph.line_spacing not in (1.5, 1.15):
                    issues.append((index, "line_spacing", shape.name,
                                   paragraph.line_spacing))
                for run in paragraph.runs:
                    if not run.text.strip():
                        continue
                    if run.font.name != "Microsoft YaHei":
                        issues.append((index, "font", shape.name, run.font.name))
                    if run.font.size and run.font.size.pt < 8:
                        issues.append((index, "font_size", shape.name, run.font.size.pt))
    with zipfile.ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            issues.append((0, "zip_crc", corrupt))
    return issues, len(prs.slides)


def main():
    path = Path(sys.argv[1])
    issues, slides = validate(path)
    print(f"=== {path.name} | {slides} 页 ===")
    if not issues:
        print("PASS —— 越界、字体、行距、字号与 ZIP CRC 全部通过")
        return 0
    for issue in issues[:100]:
        print(issue)
    print("issues", len(issues))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
