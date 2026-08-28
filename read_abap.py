"""Read ABAP source code from a BTP ABAP Environment - headless.

Examples:
    python read_abap.py class     ZCL_HELLO_WORLD
    python read_abap.py interface ZIF_HELLO
    python read_abap.py include   ZDEMO_INCLUDE
    python read_abap.py fm        Z_READ_STUFF  ZDEMO_FUGR
    python read_abap.py class ZCL_HELLO_WORLD --out ZCL_HELLO_WORLD.abap
"""

from __future__ import annotations

import argparse

from abap_session import AbapSession

# ADT source-code endpoints, keyed by the CLI sub-command.
ENDPOINTS = {
    "class":     "/sap/bc/adt/oo/classes/{name}/source/main",
    "interface": "/sap/bc/adt/oo/interfaces/{name}/source/main",
    "include":   "/sap/bc/adt/programs/includes/{name}/source/main",
    "fm":        "/sap/bc/adt/functions/groups/{group}/fmodules/{name}/source/main",
}


def build_path(kind: str, name: str, group: str | None) -> str:
    if kind == "fm" and not group:
        raise SystemExit(
            "Function modules need their function group:\n"
            "    python read_abap.py fm <name> <group>"
        )
    return ENDPOINTS[kind].format(name=name.lower(), group=(group or "").lower())


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("kind", choices=ENDPOINTS, help="object type")
    parser.add_argument("name", help="object name, e.g. ZCL_HELLO_WORLD")
    parser.add_argument("group", nargs="?", help="function group (only for 'fm')")
    parser.add_argument("--out", metavar="FILE", help="write the source to FILE")
    args = parser.parse_args()

    session = AbapSession()
    source = session.get(build_path(args.kind, args.name, args.group))

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(source)
        print(f"Wrote {len(source.splitlines())} lines to {args.out}")
    else:
        print(source)


if __name__ == "__main__":
    main()
