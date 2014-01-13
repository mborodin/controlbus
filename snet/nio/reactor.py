import threading
import select

__thread = None
__running = False

_timeout = 3

_lock = threading.Lock()

socket_map = {}

_epoll = select.epoll()


def _main_loop():
    while __running:
        with _lock:
            events = _epoll.poll(_timeout)
        for fd, event in events:
            if not fd in socket_map:
                continue
            t = socket_map[fd]
            if t.is_readable() and event & select.EPOLLIN:
                t.handle_read()
            elif t.is_writeable() and event & select.EPOLLOUT:
                t.handle_write()
            elif event & select.EPOLLERR:
                t.handle_error()
            elif event & select.EPOLLHUP:
                t.handle_close()
            elif t.is_listening():
                t.handle_incoming_connection()

    for fd in socket_map:
        t = socket_map[fd]
        t.handle_close()

    _epoll.close()


def start():
    global __thread, __running
    if __thread is not None:
        return
    __running = True
    __thread = threading.Thread(target=_main_loop)
    __thread.start()


def stop():
    global __thread, __running
    if __thread is None:
        return

    __running = False
    __thread.join()
    __thread = None


def add_transport(t):
    fd = t.fd()
    socket_map[fd] = t
    mask = select.EPOLLHUP | select.EPOLLERR
    if t.is_readable():
        mask |= select.EPOLLIN
    if t.is_writeable():
        mask |= select.EPOLLOUT
    if t.is_listening():
        mask = select.EPOLLIN | select.EPOLLET

    _epoll.register(fd, mask)


def remove_transport(t):
    with _lock:
        fd = t.fd()
        socket_map.pop(fd)
        _epoll.unregister(fd)
