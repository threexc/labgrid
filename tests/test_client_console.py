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
