import asyncore, socket, argparse, StringIO, logging, uuid


HTTP_VERBS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'OPTIONS', 'CONNECT', 'PATCH']


class ToServer(asyncore.dispatcher):
    def __init__(self, to_client_socket, logger):
        global config
        asyncore.dispatcher.__init__(self)
        self.logger = logger
        self.to_client_socket = to_client_socket
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((config.host, config.port))
        self.buffer = ''

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(8192)
        if data:
            buffer = StringIO.StringIO(data)
            response_line = buffer.readline()
            self.logger.info('Response: %s' % response_line.strip())
            self.to_client_socket.send(data)
        else:
            self.logger.info('Server closed connection')
            self.to_client_socket.close()

    def writable(self):
        return len(self.buffer) > 0

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]


class ClientHandler(asyncore.dispatcher_with_send):
    def __init__(self, socket, logger):
        asyncore.dispatcher_with_send.__init__(self, socket)
        self.to_server = ToServer(self, logger)
        self.logger = logger

    def handle_read(self):
        data = self.recv(8192)
        if data:
            buffer = StringIO.StringIO(data)
            request_line = buffer.readline().split(' ')
            if len(request_line) == 3 and request_line[0].upper() in HTTP_VERBS:
                verb, path, _ = request_line
                self.logger.info('Request: %s %s' % (verb, path))
            else:
                self.logger.info('Got non-http  message from client (%d bytes "%s"' %
                                 (len(data), str(data[:100]+'...' if len(data) > 100 else str(data))))
            self.to_server.send(data)
        else:
            self.logger.info('Client closed connection')
            self.to_server.close()


class ToClient(asyncore.dispatcher):
    def __init__(self,):
        global config
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('localhost', config.listenport))
        self.listen(5)

    def handle_accept(self):
        global config
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            logger = self.get_logger()
            logger.info('Incoming connection from %s' % repr(addr))
            ClientHandler(sock, logger)

    def get_logger(self):
        id = str(uuid.uuid4())
        logger = logging.getLogger(id)
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler('%s-%s-%s.log' % (config.host, config.port, id))
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger


def get_config():
    parser = argparse.ArgumentParser(description='Logging proxy for debugging services.')
    parser.add_argument('--host', type=str)
    parser.add_argument('--port', type=int)
    parser.add_argument('--listenport', type=int)
    return parser.parse_args()


def main():
    global config
    config = get_config()
    ToClient()
    asyncore.loop()

if __name__ == "__main__":
    main()