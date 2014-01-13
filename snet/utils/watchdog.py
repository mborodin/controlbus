from . import Timer
import time

_queue = {}


def _watchdog():
    ctime = time.time()
    for uid in _queue:
        (last, timeout, grace, callback) = _queue[uid]
        if ctime > last + (1. + grace)*timeout:
            callback(uid)

_timer = Timer(target=_watchdog)


def start(timeout=0.1):
    if not _timer.ticking:
        _timer.timeout = timeout
        _timer.start()


def stop(clear=True):
    if _timer.ticking:
        _timer.stop()
        if clear:
            _queue.clear()


def add(uid, timeout, callback, grace=0.0):
    if uid in _queue:
        raise ValueError('Duplicate id {0}'.format(uid))

    _queue[uid] = (time.time(), timeout, grace, callback)


def remove(uid):
    if not _timer.ticking:
        return
    if not uid in _queue:
        raise ValueError('Id {0} not found'.format(uid))
    _queue.pop(uid)


def touch(uid):
    if not _timer.ticking:
        return
    if not uid in _queue:
        raise ValueError('Id {0} not found'.format(uid))
    (_, timeout, grace, callback) = _queue[uid]
    _queue[uid] = (time.time(), timeout, grace, callback)
