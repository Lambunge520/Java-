import os
import runpy
import sys


def main():
    os.environ["LJM_NOGUI"] = "1"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "LJM_nogui.pyw")
    args = sys.argv[1:] or ["terminal", "--attach-console"]
    sys.argv = [script_path] + args
    runpy.run_path(script_path, run_name="__main__")


if __name__ == "__main__":
    main()
