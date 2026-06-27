#!/usr/bin/env python3
"""healing-space output validator — checks generated HTML for mandatory quality signals.
Usage: python3 scripts/validate.py <output.html>
Exit 0 = all checks pass. Exit 1 = issues found.
"""
import sys, re

def check(content, pattern, label):
    if not re.search(pattern, content, re.IGNORECASE):
        print(f"  ❌ {label}")
        return False
    print(f"  ✅ {label}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate.py <output.html>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        html = f.read()

    print(f"Validating: {sys.argv[1]}")
    all_pass = True

    # Mandatory checks
    all_pass &= check(html, r'FogExp2|fog\s*\(', "FogExp2 or fog() atmosphere")
    all_pass &= check(html, r'\*\s*\{\s*cursor\s*:\s*none\s*!important', "*{cursor:none!important} global cursor hide")
    all_pass &= check(html, r'spirit-cursor|custom.cursor|#cursor', "Custom cursor element")
    all_pass &= check(html, r'opacity\s*:\s*0', "Cursor initial opacity:0")
    all_pass &= check(html, r'lerp|\.target\s*\+|smoothstep|setTargetAtTime', "Lerp/smooth transition used")
    all_pass &= check(html, r'dt\s*=\s*Math\.min.*0\.033|dt.*clamp.*0\.033', "dt clamped to 0.033")

    # Font check
    all_pass &= check(html, r'Noto\s*Serif|Songti|SimSun|serif', "Serif/Song font family used")
    all_pass &= check(html, r'letter-spacing\s*:\s*\d{2}px', "Letter spacing >= 10px")

    # Audio safety (if audio present)
    has_audio = bool(re.search(r'AudioContext|audioCtx|OscillatorNode', html))
    if has_audio:
        all_pass &= check(html, r'432|174|triangle', "Healing frequency (432/174Hz) or triangle wave")
        all_pass &= check(html, r'gain.*0\.0[0-8]|\.gain\.value\s*=\s*0\.0', "Audio gain <= 0.08")

    print()
    if all_pass:
        print("✅ All checks passed.")
        sys.exit(0)
    else:
        print("⚠️  Issues found. Fix and re-validate.")
        sys.exit(1)

if __name__ == "__main__":
    main()
