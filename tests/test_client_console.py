import sys
import textwrap

import pexpect

from labgrid.remote.client import ConsoleEscape


def test_console_escape_feed():
    esc = ConsoleEscape()
    assert esc.feed(b"ls\r") == (b"ls\r", [])
    assert esc.feed(b"a\x14ob\x14fc\x14c\x14g") == (b"abc", ["on", "off", "cycle", "get"])
    assert esc.feed(b"\x14\x14") == (b"\x14", [])
    assert esc.feed(b"\x14?") == (b"", ["help"])
    # prefix split across reads
    assert esc.feed(b"x\x14") == (b"x", [])
    assert esc.feed(b"c") == (b"", ["cycle"])


SCRIPT = textwrap.dedent("""
    import asyncio
    from labgrid.remote.client import ClientSession

    class Power:
        state = False
        def on(self): self.state = True
        def off(self): self.state = False
        def cycle(self): self.state = True
        def get(self): return self.state

    class Session:
        _console_pty = ClientSession._console_pty
        def _get_power_driver(self, target, name=None):
            return Power()

    async def main():
        with Session()._console_pty(None) as kwargs:
            p = await asyncio.create_subprocess_exec("cat", **kwargs)
            print("ready", flush=True)
            await p.wait()

    asyncio.run(main())
""")


def test_console_pty_power_keys():
    with pexpect.spawn(sys.executable, ["-c", SCRIPT], timeout=10) as spawn:
        spawn.expect("ready")
        spawn.send("hello\r")
        spawn.expect("hello")
        spawn.send("\x14g")
        spawn.expect(r"\[labgrid\] power is off")
        spawn.send("\x14o")
        spawn.expect(r"\[labgrid\] power on done")
        spawn.send("\x14g")
        spawn.expect(r"\[labgrid\] power is on")
        spawn.send("\x14h")
        spawn.expect(r"\[labgrid\] Ctrl-T then")
        # EOF through the pty ends cat
        spawn.send("\x04")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0
