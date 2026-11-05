import sys
import textwrap

import pexpect

from labgrid.remote.client import ConsolePrompt


def test_console_prompt_edit():
    prompt = ConsolePrompt(["power on", "power off"])
    assert prompt.start() == b"\r\nlabgrid> "
    assert prompt.feed(b"powr\x7fer on") == (b"powr\b \ber on", None, b"")
    assert prompt.feed(b"\rrest") == (b"\r\n", "enter", b"rest")
    assert prompt.line == "power on"

    prompt.start()
    assert prompt.feed(b"x\x03y") == (b"x\r\n", "cancel", b"y")
    prompt.start()
    assert prompt.feed(b"\x14") == (b"\r\n", "literal", b"")


def test_console_prompt_complete():
    prompt = ConsolePrompt(["power on", "power off", "power cycle"])
    prompt.start()
    assert prompt.feed(b"p\t") == (b"power ", None, b"")
    assert prompt.feed(b"\t") == (b"\r\npower cycle  power off  power on\r\nlabgrid> power ", None, b"")
    assert prompt.feed(b"o\t") == (b"o\r\npower off  power on\r\nlabgrid> power o", None, b"")
    assert prompt.feed(b"f\t") == (b"ff", None, b"")
    assert prompt.line == "power off"
    assert prompt.feed(b"x\t") == (b"x\a", None, b"")


def test_console_prompt_escape():
    prompt = ConsolePrompt(["power on"])
    prompt.start()
    # arrow keys and Alt+key are ignored, also when split across reads
    assert prompt.feed(b"a\x1b[Ab\x1bOBc\x1bxd") == (b"abcd", None, b"")
    assert prompt.feed(b"\x1b") == (b"", None, b"")
    assert prompt.feed(b"[1;5De") == (b"e", None, b"")
    assert prompt.line == "abcde"


SCRIPT = textwrap.dedent("""
    import asyncio
    import sys
    from labgrid.remote.client import ClientSession

    class Session:
        _console_pty = ClientSession._console_pty

    async def main():
        with Session()._console_pty(sys.argv[1:]) as (call, kwargs):
            p = await asyncio.create_subprocess_exec(*call, **kwargs)
            print("ready", flush=True)
            await p.wait()

    asyncio.run(main())
""")


def test_console_pty():
    with pexpect.spawn(sys.executable, ["-c", SCRIPT, "cat"], timeout=10) as spawn:
        spawn.expect("ready")
        spawn.send("hello\r")
        spawn.expect("hello")
        # EOF through the pty ends cat
        spawn.send("\x04")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0


def test_console_pty_ctty():
    # /dev/tty can only be opened with a controlling terminal
    prog = [sys.executable, "-c", "open('/dev/tty'); print('has ctty')"]
    with pexpect.spawn(sys.executable, ["-c", SCRIPT, *prog], timeout=10) as spawn:
        spawn.expect("has ctty")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0
