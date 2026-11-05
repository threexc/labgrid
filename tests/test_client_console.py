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

    class Power:
        state = False
        def on(self): self.state = True
        def off(self): self.state = False
        def cycle(self): self.state = True
        def get(self): return self.state

    class Session:
        _console_pty = ClientSession._console_pty
        _console_commands = ClientSession._console_commands
        power = Power()
        def _get_power_driver(self, target, name=None):
            return self.power

    async def main():
        with Session()._console_pty(None, sys.argv[1:]) as (call, kwargs):
            p = await asyncio.create_subprocess_exec(*call, **kwargs)
            print("ready", flush=True)
            await p.wait()

    asyncio.run(main())
""")


def test_console_pty_commands():
    with pexpect.spawn(sys.executable, ["-c", SCRIPT, "cat"], timeout=10) as spawn:
        spawn.expect("ready")
        spawn.send("hello\r")
        spawn.expect("hello")
        # Tab completion and running a command
        spawn.send("\x14power g\t")
        spawn.expect("labgrid> power get")
        spawn.send("\r")
        spawn.expect(r"\[labgrid\] power is off")
        spawn.send("\x14power on\r")
        spawn.expect(r"\[labgrid\] power on done")
        spawn.send("\x14power get\r")
        spawn.expect(r"\[labgrid\] power is on")
        spawn.send("\x14help\r")
        spawn.expect(r"\[labgrid\] power cycle +switch power off and on again")
        spawn.send("\x14nope\r")
        spawn.expect(r"\[labgrid\] unknown command 'nope'")
        # q leaves the prompt, then input goes to the target again
        spawn.send("\x14q\r")
        spawn.expect("labgrid> q\r\n")
        spawn.send("world\r")
        spawn.expect("world\r\nworld")
        # Ctrl-T Ctrl-T sends a literal Ctrl-T, echoed back by the pty
        spawn.send("\x14\x14")
        spawn.expect_exact("labgrid> \r\n^T")
        # EOF through the pty ends cat
        spawn.send("\r\x04")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0


def test_console_pty_hold_output():
    with pexpect.spawn(sys.executable, ["-c", SCRIPT, "sh", "-c", "sleep 1; echo late; sleep 2"], timeout=10) as spawn:
        spawn.expect("ready")
        spawn.send("\x14")
        spawn.expect("labgrid> ")
        # output is held back while the prompt is open ...
        assert spawn.expect(["late", pexpect.TIMEOUT], timeout=2) == 1
        # ... and shown after leaving it
        spawn.send("\x03")
        spawn.expect("late")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0


def test_console_pty_ctty():
    # /dev/tty can only be opened with a controlling terminal
    prog = [sys.executable, "-c", "open('/dev/tty'); print('has ctty')"]
    with pexpect.spawn(sys.executable, ["-c", SCRIPT, *prog], timeout=10) as spawn:
        spawn.expect("has ctty")
        spawn.expect(pexpect.EOF)
    assert spawn.exitstatus == 0
