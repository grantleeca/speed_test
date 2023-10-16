import random
import socket
import string
import time


def RandomChar():
    return random.choice(string.digits + string.ascii_letters + string.punctuation)


BLOCK_SIZE = 4096
BLOCK_CONTENT = ''.join([RandomChar() for _ in range(BLOCK_SIZE)]).encode()


class TCPClient:
    def __init__(self, logger, s: socket.socket):
        self._logger = logger
        self._conn = s if s else socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, addr):
        self._logger.debug(f"Begin connect to {addr}")
        self._conn.connect(addr)
        self._logger.info(f"Connected {addr}.")

    def send_command(self, buf: str):
        self._conn.sendall(buf.encode())
        return self._conn.recv(1024).decode()

    def send_test_block(self, size):
        while size > 0:
            write_size = min(BLOCK_SIZE, size)
            self._conn.sendall(BLOCK_CONTENT[:write_size])
            size -= write_size

        return self._conn.recv(1024).decode()

    def recv_test_block(self, count):
        self._conn.sendall(f'Send {count}'.encode())

        while count > 0:
            buf = self._conn.recv(8192).strip()
            count -= len(buf)

    def say_hello(self):
        return self.send_command('SpeedTest V1')

    def say_bye(self):
        resp = self.send_command('Bye')
        self._logger.info(f"Response: {resp}")

    def download(self, period):
        time_stamp = 0.0
        ts = 0.0
        kb = 0
        size = BLOCK_SIZE
        max_speed = 0.0

        while ts < period:
            start_time = time.perf_counter()
            self.recv_test_block(size)
            ts = time.perf_counter() - start_time

            max_speed = max(max_speed, size / 1024.0 / ts)
            self._logger.info("Download time: %fs. size %d K. speed: %.2f KB/S" % (ts, size / 1024, size / 1024 / ts))

            time_stamp += ts
            kb += size / 1024
            size *= 2

        if max_speed > 1024.0:
            self._logger.info("Max download speed: %.2f MB/S" % (max_speed / 1024))
        else:
            self._logger.info("Max download speed: %.2f KB/S" % max_speed)

    def upload(self, period):
        time_stamp = 0.0
        kb = 0
        ts = 0
        size = BLOCK_SIZE
        max_speed = 0.0

        while ts < period:
            self.send_command(f"Recv {size}")

            start_time = time.perf_counter()
            self.send_test_block(size)
            ts = time.perf_counter() - start_time

            max_speed = max(max_speed, size / 1024 / ts)
            self._logger.info("Upload time: %fs. size %d K. speed: %.2f KB/S" % (ts, size / 1024, size / 1024 / ts))

            time_stamp += ts
            kb += size / 1024
            size *= 2

        if max_speed > 1024.0:
            self._logger.info("Max upload speed: %.2f MB/S" % (max_speed / 1024))
        else:
            self._logger.info("Max upload speed: %.2f KB/S" % max_speed)

    def start(self, period=3.0):
        resp = self.say_hello()
        if resp.upper() == 'OK':
            self.download(period)
            self.upload(period)

            self.say_bye()
        else:
            self._logger.warning("Login error: %s" % resp)


class UDPClient:
    def __init__(self, logger, s=None):
        self._logger = logger
        self._conn = s if s else socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._addr = None

    def connect(self, addr):
        self._logger.info("UDP address: %s:%d" % addr)
        self._addr = addr

    def send_cmd(self, cmd):
        self._logger.debug(f"Send command: {cmd}")
        self._conn.sendto(cmd.encode(), self._addr)
        msg = self._conn.recvfrom(8192)
        return msg[0].decode()

    def recv_test_block(self, count):
        self._conn.sendto(f"Send {count}".encode(), self._addr)

        while count > 0:
            recv = self._conn.recvfrom(8 * 1024)
            count -= len(recv[0])

    def send_test_block(self, size):
        count = size

        while count > 0:
            write_size = BLOCK_SIZE if count > BLOCK_SIZE else count
            # buf = RandomChar() * write_size
            self._conn.sendto(BLOCK_CONTENT, self._addr)
            count -= write_size

        self._logger.debug("Send %dM data finished. waiting for acknowledge." % (size / 1024 / 1024))

        msg = self._conn.recvfrom(1024)
        return msg[0].decode()

    def say_hello(self):
        result = self.send_cmd("SpeedTest V1")
        return True if result.upper() == 'OK' else False

    def say_bye(self):
        msg = self.send_cmd('Bye')
        self._logger.info('Say bye return: %s' % msg)

    def download(self, period):
        start_time = time.perf_counter()
        time_stamp = 0.0
        number = 0
        n = 1

        while time_stamp < period:
            self.recv_test_block(n * BLOCK_SIZE)

            time_stamp = time.perf_counter() - start_time
            number += n
            n *= 2

        mb = number * BLOCK_SIZE / 1024 / 1024
        self._logger.info("Download time: %fs. size %dM. speed: %.2f MB/S" % (time_stamp, mb, mb / time_stamp))

    def upload(self, period):
        start_time = time.perf_counter()
        time_stamp = 0.0
        number = 0
        n = 1
        while time_stamp < period:
            size = n * BLOCK_SIZE
            self.send_cmd(f"Recv {size}")
            self.send_test_block(size)

            time_stamp = time.perf_counter() - start_time
            number += n
            n *= 2

        mb = number * BLOCK_SIZE / 1024 / 1024
        self._logger.info("Upload time: %fs. size %dM. speed: %.2f MB/S" % (time_stamp, mb, mb / time_stamp))

    def start(self, period):
        self._logger.info('Begin UDP send.')

        if self.say_hello():
            self._logger.info('Say hello OK.')
            self.download(period)
            self.upload(period)

            self.say_bye()
        else:
            self._logger.info('Invalid server.')
