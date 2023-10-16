import random
import socketserver
import string

BLOCK_SIZE = 65536
BLOCK_CONTENT = ''.join([random.choice(string.digits + string.ascii_letters) for _ in range(BLOCK_SIZE)]).encode()


class SpeedTCPHandler(socketserver.BaseRequestHandler):
    logger = None

    def recv_cmd(self):
        cmd = self.request.recv(1024).strip().decode()
        self.logger.debug("Recv command: %s" % cmd)
        return cmd

    def send_acknowledge(self, msg=None):
        if msg:
            self.logger.info("send acknowledge: %s" % msg)
            self.request.sendall(msg.encode())
        else:
            self.request.sendall('OK'.encode())

    def send_test_block(self, size):
        while size > 0:
            size -= self.request.send(BLOCK_CONTENT[:min(BLOCK_SIZE, size)])

    def recv_test_block(self, size):
        while size > 0:
            buf = self.request.recv(8192).strip()
            size -= len(buf)

    def handle(self):
        self.logger.info(f"{self.client_address} linked.")

        while True:
            cmd = self.recv_cmd().lower().split(' ')
            if cmd[0] == 'speedtest':
                if len(cmd) > 1 and cmd[1] == 'v1':
                    self.send_acknowledge()
                else:
                    self.send_acknowledge("Unsupported protocol version.")
                    break

            elif cmd[0] == 'bye':
                self.send_acknowledge("Good bye.")
                break

            elif cmd[0] == 'send':
                if len(cmd) > 1:
                    size = int(cmd[1])
                    self.send_test_block(size)
                    self.logger.debug("Send %d KB data finished." % (size / 1024))
                else:
                    self.send_acknowledge("Not size parameter.")
                    break

            elif cmd[0] == 'recv':
                if len(cmd) > 1:
                    size = int(cmd[1])
                    self.send_acknowledge()

                    self.recv_test_block(size)
                    self.send_acknowledge()

                    self.logger.debug("Recv %d KB data finished." % (size / 1024))
                else:
                    self.send_acknowledge("Not size parameter.")
                    break

            else:
                self.send_acknowledge("Unknown command: " % cmd)
                break


class UDPAcknowledge:
    def __init__(self, logger, socket, addr):
        self.logger = logger
        self.socket = socket
        self.addr = addr

    def reply(self, msg=None):
        if msg:
            self.logger.info('Send message: %s' % msg)
        else:
            msg = 'OK'

        self.socket.sendto(msg.encode(), self.addr)

    def send_test_block(self, size):
        count = size

        while count > 0:
            write_size = min(BLOCK_SIZE, count)
            self.socket.sendto(BLOCK_CONTENT[:write_size], self.addr)
            count -= write_size

        self.logger.debug("Send %d K data finished." % (size / 1024))


class SpeedUDPHandler(socketserver.BaseRequestHandler):
    logger = None
    count = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def set_count(cls, count):
        cls.count = count

    @classmethod
    def get_count(cls):
        return cls.count

    @classmethod
    def recv_count(cls, size):
        cls.count -= size
        return cls.count

    def handle(self):
        ack = UDPAcknowledge(self.logger, socket=self.request[1], addr=self.client_address)
        data = self.request[0].strip()
        if self.get_count() > 0:
            self.logger.debug(f"Recv data: {data[:8]}")
            self.logger.debug("Waiting data for %d, Recv data %d." % (self.get_count(), len(data)))
            if self.recv_count(len(data)) <= 0:
                ack.reply()
            return

        msg = data.decode()
        if len(msg) > 1024:
            self.logger.warning("Invalid command, count = %d" % self.count)
            return

        self.logger.debug("from {} recv {}".format(self.client_address[0], msg))

        cmd = msg.lower().split(' ')
        if cmd[0] == 'speedtest':
            if len(cmd) > 1 and cmd[1] == 'v1':
                ack.reply()
            else:
                ack.reply("Unsupported protocol version: %s." % msg)

        elif cmd[0] == 'send':
            if len(cmd) > 1:
                ack.send_test_block(int(cmd[1]))

        elif cmd[0] == 'recv':
            if len(cmd) > 1:
                SpeedUDPHandler.count = int(cmd[1])
                ack.reply()
            else:
                ack.reply("Not size parameter.")

        elif cmd[0] == 'bye':
            ack.reply("Good bye.")

        else:
            ack.reply("Unknown command: %s" % msg)
