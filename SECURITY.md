# Security

## How NT Goat Studio protects you

NT Goat Studio runs a small web server on your own computer so you can use it from your browser. It is built to stay private and harmless:

| Protection | What it means |
|---|---|
| **Local only** | The server listens on `127.0.0.1`. Other computers on your network or the internet cannot connect to it |
| **Session token** | Each time the Studio starts it creates a random secret. Only the Studio page knows it, and every request without it is refused. A website open in another tab cannot control the Studio, read your ROM or write files |
| **Host check** | Requests addressed to any other host name are refused, which blocks "DNS rebinding" tricks |
| **No network access** | The tool never downloads or uploads anything. No telemetry, no update checks |
| **Read-only on your ROM** | Your original ROM is only read. The patched ROM is written to a new file that you choose |
| **Upload limit** | Files over 256 MB are refused |
| **No dependencies** | Only the Python standard library, so there are no third-party packages to trust |

## Good habits
- Download the tool only from this repository or its Releases page.
- Stop the Studio (close its terminal window) when you're done.
- Don't run it with administrator rights; it doesn't need them.
- Don't change the address to `0.0.0.0` to use it from another device: that would expose it to your network.

## Reporting a problem
If you find a security issue, please open an issue titled **"Security"** without details, or contact the author through GitHub, and the details can be shared privately. Please never attach ROMs, saves or game files to an issue.

## Legal reminder
This repository contains no game data. Use the tool only with a ROM dumped from a cartridge you own, and never distribute ROMs or patched ROMs.
