"""One command for the whole build: data -> custom visual -> Power BI project.

    python tools/rebuild.py                  local project in pbip-local/ (reads the workbook from disk)
    python tools/rebuild.py --publish        the committed pbip/ folder (reads the workbook from GitHub)
    python tools/rebuild.py --skip-visual    reuse dist/EgyptPulse.pbiviz

Needs Node.js for the visual (run `npm ci` in visual/ once). On Windows keep the clone path short:
Power BI project paths are deep and MAX_PATH is 260 characters.
"""
import shutil
import subprocess
import sys
from pathlib import Path

EG = Path(__file__).absolute().parent.parent
PY = sys.executable
PBIVIZ = EG / "dist" / "EgyptPulse.pbiviz"
REPO_RAW = "https://raw.githubusercontent.com/Moataz-Elmesmary/egypt-market-intelligence/main"


def run(cmd, cwd=None, shell=False):
    r = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        print(out[-3000:])
        raise SystemExit(f"failed: {cmd}")
    return out


def main():
    args = sys.argv[1:]
    print(run([PY, str(EG / "build_egypt_data.py")]))
    if "--skip-visual" not in args:
        out = run("npx pbiviz package --no-stats", cwd=EG / "visual", shell=True)
        if "Package created" not in out and "package created" not in out.lower():
            print(out[-2000:])
            raise SystemExit("visual build failed")
        pkg = max((EG / "visual" / "dist").glob("*.pbiviz"), key=lambda p: p.stat().st_mtime)
        PBIVIZ.parent.mkdir(exist_ok=True)
        shutil.copy(pkg, PBIVIZ)
        print("visual packaged ->", PBIVIZ.relative_to(EG))
    if "--publish" in args:
        print(run([PY, str(EG / "build_pbip.py"), str(PBIVIZ), str(EG / "pbip"),
                   "--data-url", f"{REPO_RAW}/data/Egypt_Market_Intelligence_2026.xlsx"]))
        print(run([PY, str(EG / "tools" / "metrics.py")]))
    else:
        print(run([PY, str(EG / "build_pbip.py"), str(PBIVIZ), str(EG / "pbip-local")]))


if __name__ == "__main__":
    main()
