"""Prove the pipe works before reading real objects.

Fetches the ADT "core discovery" document - a cheap, always-present endpoint.
A clean run means: .env is correct, OAuth succeeded, and the ADT API answered.
"""

from abap_session import AbapSession


def main() -> None:
    session = AbapSession()
    xml = session.get("/sap/bc/adt/core/discovery", accept="application/atomsvc+xml")
    print(f"OK - connected to {session.host}")
    print(f"     ADT discovery document is {len(xml)} bytes")


if __name__ == "__main__":
    main()
