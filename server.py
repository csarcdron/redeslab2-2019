#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
import connection
import threading
import os
import sys
from constants import *


class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """
    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print("Serving %s on %s:%s." % (directory, addr, port))
        self.directory = directory
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((addr, port))
        # Este socket lo utilizaremos para atender nuevas conexiones
        # entrantes por lo tanto solo necesitamos escuchar de a 1 cliente
        # Luego el procesamiento de cada cliente sera utilizando hilos.
        self.s.listen(1)
        self.connections = []
        self.threads = []

    def serve(self):
        """
        Loop principal del servidor. Se acepta una conexión a la vez
        y se espera a que concluya antes de seguir.
        """
        while True:
            try:
                clientSocket, serverAddress = self.s.accept()
                clientSocket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR, 1)
                self.connections.append(connection.Connection(clientSocket,
                                                              self.directory))
                self.threads.append(threading.Thread(
                    target=self.connections[len(self.connections) - 1].handle,
                    args=()))
                # Iniciamos el ultimo hilo ingresado a la lista de hilos
                self.threads[len(self.threads) - 1].start()

                # Hacemos limpieza de la lista de hilos
                self.clean_threads()

            except Exception as e:
                print("Error interno del servidor.\n")
                print(e)

            except KeyboardInterrupt:
                # Captura para que si se hace Ctrl+C solo muestre un mensaje
                print("\nClosing Server...")
                sys.exit()

    def clean_threads(self):
        for i, thr in enumerate(self.threads):
            if not(thr.is_alive()):
                del(self.threads[i])
                del(self.connections[i])


def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help="Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help="Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)

    if(not os.path.isdir(options.datadir)):
        try:
            print("Se crea directorio: %s" % options.datadir)
            os.makedirs(options.datadir)
        except OSError as e:
            print(e)
            sys.exit(1)
    try:
        port = int(options.port)
        server = Server(options.address, port, options.datadir)
        server.serve()

    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
