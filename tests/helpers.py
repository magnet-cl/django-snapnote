calls = []


def nobody(user):
    return False


def failing(ticket, url):
    raise RuntimeError("boom")


def record(ticket, url):
    calls.append((ticket, url))
