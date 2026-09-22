"""Prints the Kiota version the generated code's lock file names, so CI installs exactly that one."""
import json

print(json.load(open("src/Xio.Parallax.Client/Generated/kiota-lock.json", encoding="utf-8"))["kiotaVersion"])
