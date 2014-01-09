import signal
import sys
import os


def sighandler(sig):
    def decorated(f):
        signal.signal(sig, f)
        return f
    return decorated


def sighup(f):
    @sighandler(signal.SIGHUP)
    def decorated(*args, **kwargs):
        f(*args, **kwargs)
    return decorated


def sigint(f):
    @sighandler(signal.SIGINT)
    def decorated(*args, **kwargs):
        f(*args, **kwargs)
    return decorated


def sigterm(f):
    @sighandler(signal.SIGTERM)
    def decorated(*args, **kwargs):
        f(*args, **kwargs)
    return decorated


def sigfinish(f):
    @sigint
    @sigterm
    def decorated(*args, **kwargs):
        f(*args, **kwargs)
    return decorated


def daemon(**confargs):
    def decorated(f):
        def run_daemon(*args, **kwargs):
            log = None if not 'log' in confargs else confargs['log']
            try:
                pid = os.fork()
                if pid > 0:
                    sys.exit(0)  # Parent should exit
            except OSError as e:
                msg = 'Fork failed: %s' % e.strerror
                if not log is None:
                    log.critical(msg)
                else:
                    sys.stderr.write('[CRITICAL] %s\n' % msg)
                sys.exit(1)
            chroot = '/' if not 'chroot' in confargs else confargs['chroot']
            pidfile = None if not 'pidfile' in confargs \
                else confargs['pidfile']
            umask = 0 if not 'umask' in confargs else confargs['umask']

            os.chdir(chroot)
            os.setsid()
            os.umask(umask)

            try:
                pid = os.fork()
                if pid > 0:
                    sys.exit(0)
            except OSError as e:
                msg = 'Fork failed: %s' % e.strerror
                if not log is None:
                    log.critical(msg)
                else:
                    sys.stderr.write('[CRITICAL] %s\n' % msg)
                sys.exit(1)

            if not pidfile is None:
                def delpid():
                    os.remove(pidfile)
                import atexit
                atexit.register(delpid)
                pid = str(os.getpid())
                try:
                    fout = open(pidfile, 'w+')
                    fout.write('%s\n' % pid)
                    fout.close()
                except IOError as e:
                    msg = 'Can not create pid file: %s' % e.strerror
                    if not log is None:
                        log.warning(msg)
                    else:
                        sys.stderr.write('[WARN] %s\n' % msg)
                    sys.exit(1)

            return f(*args, **kwargs)
        return run_daemon
    return decorated
