"""Execute the selected data-free documentation examples in temporary directories."""

from pathlib import Path
import os
import re
import tempfile


DOCS = Path(__file__).resolve().parents[1]
PAGES = (
    "getting-started/quickstart.mdx",
    "tutorials/delivery-experiments.mdx",
    "tutorials/environment-analysis.mdx",
    "reference/trajectories.mdx",
    "reference/terrain.mdx",
    "reference/illumination-power.mdx",
    "reference/communications.mdx",
    "reference/scheduling.mdx",
    "reference/validation-exports.mdx",
)


def main():
    previous = Path.cwd()
    count = 0
    try:
        for relative in PAGES:
            page = DOCS / relative
            blocks = re.findall(r"^```python\n(.*?)^```", page.read_text(), re.M | re.S)
            namespace = {"__name__": "__documentation_example__"}
            with tempfile.TemporaryDirectory(prefix="soma-doc-example-") as temporary:
                os.chdir(temporary)
                for index, block in enumerate(blocks, start=1):
                    exec(compile(block, f"{page}:python-block-{index}", "exec"), namespace)
                    count += 1
            print(f"PASS {relative}: {len(blocks)} Python blocks")
    finally:
        os.chdir(previous)
    print(f"Executed {count} data-free Python blocks across {len(PAGES)} pages.")
    print("Kernel/raster preparation and physical examples were not executed by this check.")


if __name__ == "__main__":
    main()
