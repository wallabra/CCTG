import socket
import sys
import threading
import time

import dataparser
import socketeer


class CCT(object):
    def __init__(self, ips, host, port=8000, game_name=""):
        self.client_list = []
        self.ip_bans = []
        self.num_connections = 0
        self.parser = dataparser.CCTGParser(game_name)
        self.start_time = time.time()
        self.host = host

        if host:
            self.game_code = open("games\\{}\\statecode.pec".format(game_name)).readlines()

        ip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_socket.connect(('google.com', 0))

        self.our_ip, self.our_port = ip_socket.getsockname()[0], port

        ip_socket.close()

        print "Starting connections: " + " ".join(ips)

        for x in ips:
            self.num_connections += 1

            try:
                ip = x.split(":")[0]
                port = int(x.split(":")[1])

            except IndexError:
                continue

            self.add_connection(ip, port)

        print "Doing listening loop as {}:{}!".format(self.our_ip, self.our_port)

        threading.Thread(name="Listening Loop", target=self.listening_loop, args=()).start()

        if host:
            threading.Thread(name="Game Loop", target=self.game_loop, args=()).start()

        while True:
            data_to_send_to_network = raw_input("> ")
            for client in self.client_list:
                socketeer.send_to_socket(client["client"], data_to_send_to_network + "\n")

    def game_loop(self):
        for code in self.game_code:
            eval(code)

    def add_connection(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        sock.setblocking(False)
        client_index = len(self.client_list)
        self.client_list.append({"client": sock, "ip": ip, "port": port})
        threading.Thread(name="Connection {}".format(client_index + 1), target=self.connection_loop,
                         args=(client_index,))

    def listening_loop(self):
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.setblocking(False)
        listening_socket.bind((self.our_ip, int(self.our_port)))
        listening_socket.listen(2)

        while True:
            try:
                (client, (ip, port)) = listening_socket.accept()

            except socket.error:
                continue

            else:
                break

        while True:

            if ip in self.ip_bans:
                socketeer.send_to_socket(client, "ERR BANNED_CLIENT\n")
                continue

            self.client_list.append({"client": client, "ip": ip, "port": port})

            socketeer.send_to_socket(client, "IPS " + " ".join(
                [":".join((x["ip"], str(x["port"]))) for x in self.client_list]) + "\n")

            if self.host:
                socketeer.send_to_socket(client, "IAMHOST")

            socketeer.send_to_socket(client, "GAMESTATE START\n")
            socketeer.send_to_socket(client, "\n".join(["{} {} {} {}".format(
                game_data["scope"] + (" " + game_data["client_ip"] if game_data["client_ip"] == "user" else ""),
                game_data["name"],
                game_data["type"],
                game_data["content"]
            ) for game_data in self.parser.game_state.game_data.values()]))
            socketeer.send_to_socket(client, "GAMESTATE END\n")

    def connection_loop(self, client_index):
        try:
            while True:
                try:
                    client_dict = self.client_list[client_index]

                except KeyError:
                    return

                raw = ""

                while True:
                    try:
                        raw += client_dict["client"].recv(4096)

                    except socket.error:
                        continue

                    if not raw.endswith("\n"):
                        continue

                for data in raw.split("\n"):
                    self.client_list = self.parser.parse_cctg_data(self.client_list, client_dict["client"], data)

        finally:
            return

    def __del__(self):
        for client in self.client_list:
            socketeer.send_to_socket(client["client"], "TERMINATINGCLIENT {} {}".format(self.our_ip, self.our_port))

        print "Server ran for {} seconds!".format(time.time() - self.start_time)


if __name__ == "__main__":
    print "Starting connections!"
    if sys.argv[1].upper() == "HOST":
        try:
            CCT(sys.argv[4:], False, sys.argv[3], sys.argv[2])

        except IndexError:
            CCT([], False, sys.argv[3], sys.argv[2])

    else:
        CCT(sys.argv[2:], False, sys.argv[1])
