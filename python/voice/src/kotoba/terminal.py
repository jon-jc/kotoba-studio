"""Start a persistent Windows PowerShell console with explicit Unicode pipes."""

import base64


def powershell_arguments():
    # EncodedCommand is decoded before stdin is read, so even the first
    # Japanese command sees UTF-8 rather than the machine's OEM code page.
    setup = "$utf8 = New-Object System.Text.UTF8Encoding($false); [Console]::InputEncoding=$utf8; [Console]::OutputEncoding=$utf8; $OutputEncoding=$utf8"
    encoded = base64.b64encode(setup.encode("utf-16-le")).decode("ascii")
    return ["-NoLogo", "-NoProfile", "-NoExit", "-OutputFormat", "Text", "-EncodedCommand", encoded]
