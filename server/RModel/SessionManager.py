import asyncio
import socket
import uvloop
from pickle import loads
from pprint import pprint
import Session


class SessionManager:

    def __init__(self, host='0.0.0.0', port=12346):
        self.host = host
        self.port = port

        self.session_list = {}
        self.tokens = {}
        # Create tcp socket for accept
        # typical socket set up commands
        print((host, port))
        self.master_socket = socket.socket()
        self.master_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.master_socket.setblocking(False)
        self.master_socket.bind((host, port))
        self.master_socket.listen(socket.SOMAXCONN)
        self.loop = asyncio.get_event_loop()
        print(f'Start server on {host}:{port}')

    async def serv(self):
        while True:
            print('serving....')
            sock, addr = await self.loop.sock_accept(self.master_socket)
            sock.setblocking(False)
            asyncio.ensure_future(self.handle_solver(sock, addr))
            print(f'new connection to SessionManager from {addr}')

    async def handle_solver(self, sock, addr):
        data = await self.loop.sock_recv(sock, 1024)
        param = loads(data)
        pprint(param)
        if param['USER'] is not 'u000000':
            try:
                current_session = self.session_list[param['USER-TOKEN']]
            except KeyError:
                current_session = self.session_list[param['USER-TOKEN']] = Session.Session(sock, addr, Session.NAMED)
            finally:
                await current_session.recieve_connection(sock, addr)
        else:
            raise NotImplementedError


if __name__ == '__main__':
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()

    server = SessionManager()
    asyncio.ensure_future(server.serv())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
    loop.close()