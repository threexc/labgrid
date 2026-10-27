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
