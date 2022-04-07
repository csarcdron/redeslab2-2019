# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
import sys
from os import listdir, path
from constants import *
from base64 import b64encode


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        self.s = socket
        self.directory = directory + "/"
        self.input_buffer = ""
        self.output_buffer = ""
        self.connected = True

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        while(self.connected):
            try:
                self.input_buffer += self.s.recv(4096).decode("ascii")

                # Si el cliente se desconecta sin mandar quit esto hace que
                # envie un request vacio, por lo tanto llamamos al metodo quit
                # para que cierre la conexion
                if self.input_buffer == "":
                    self.connected = False

                if (EOL in self.input_buffer):
                    # Se hace split del input_buffer dividiendolo por EOL,
                    # hasta la primera ocurrencia, luego se toma el primer
                    # elemento de esa lista, el cual es un potencial comando y
                    # se guarda el mismo en request
                    request = self.input_buffer.split(EOL, 1)[0]
                    # Se modifica el input_buffer con un replace quitandole el
                    # comando que obtuvimos, le añadimos EOL al final para que
                    # sea el comando original del input_buffer y reemplazamos
                    # por un string vacio solo la primer ocurrencia del mismo
                    self.input_buffer = self.input_buffer.replace(
                                            request + EOL, "", 1)
                    if request:
                        self.parse_request(request)
                    self.send_data_to_client()

            except UnicodeDecodeError:
                self.add_status_code_to_output(BAD_REQUEST)
                self.send_data_to_client()

            except Exception as e:
                print("Error interno del servidor.\n")
                print(e)
                self.add_status_code_to_output(INTERNAL_ERROR)
                self.send_data_to_client()

        # Si el cliente manda quit() o se desconecta (esto hace que envie un
        # string vacio) self.connected se vuelve false y cerramos el socket
        self.s.close()
        # Matamos el hilo que se encarga de correr el objeto connection
        # desde el mismo objeto llamando a sys.exit()
        sys.exit()

    def parse_request(self, request):
        command = request.split()[0]
        if is_valid_command(command):
            if command == "get_file_listing":
                if len(request.split()) == 1:
                    self.get_file_listing()
                else:
                    self.add_status_code_to_output(INVALID_ARGUMENTS)

            if command == "get_metadata":
                if len(request.split()) == 2:
                    try:
                        filename = request.split()[1]
                        # Chequea si los caracteres de filename estan
                        # contenidos dentro del conjunto de caracteres validos
                        # especificados en VALID_CHARS
                        if (set(filename) <= VALID_CHARS):
                            self.get_metadata(filename)
                        else:
                            self.add_status_code_to_output(FILE_NOT_FOUND)
                    except Exception as e:
                        print("Error interno del servidor.\n")
                        print(e)
                        self.add_status_code_to_output(INTERNAL_ERROR)
                else:
                    self.add_status_code_to_output(INVALID_ARGUMENTS)

            if command == "get_slice":
                if len(request.split()) == 4:
                    splitted_request = request.split()
                    filename = splitted_request[1]
                    offset = splitted_request[2]
                    size = splitted_request[3]
                    # Chequea si se envio un offset o size punto flotante y
                    # convierte el nombre del archivo en un conjunto para
                    # ver si esta contenido dentro del conjunto de
                    # caracteres validos especificados en VALID_CHARS
                    if ("." not in (offset + size) and
                            set(filename) <= VALID_CHARS):
                        try:
                            offset = int(offset)
                            size = int(size)
                            self.get_slice(filename, offset, size)
                        # Tira una excepcion si offset o size es una cadena
                        # que contiene cosas distintas de digitos en la
                        # conversion a int
                        except ValueError:
                            self.add_status_code_to_output(
                                INVALID_ARGUMENTS)
                    else:
                        self.add_status_code_to_output(INVALID_ARGUMENTS)
                else:
                    self.add_status_code_to_output(INVALID_ARGUMENTS)

            if command == "quit":
                if len(request.split()) == 1:
                    self.quit()
                else:
                    self.add_status_code_to_output(INVALID_ARGUMENTS)
        else:
            if ("\n" in request):
                self.add_status_code_to_output(BAD_EOL)
            else:
                self.add_status_code_to_output(INVALID_COMMAND)

    def get_file_listing(self):
        self.add_status_code_to_output(CODE_OK)
        filelist = listdir(self.directory)

        for filename in filelist:
            self.add_to_output(filename + EOL)
        self.add_to_output(EOL)

    def get_metadata(self, filename):
        try:
            file_size = path.getsize(self.directory + filename)
            self.add_status_code_to_output(CODE_OK)
            self.add_to_output(str(file_size) + EOL)
        except FileNotFoundError:
            self.add_status_code_to_output(FILE_NOT_FOUND)
        except OSError as e:
            # La excepcion captura cuando el filename es
            # demasiado largo (errno (error number) = 36)
            if e.errno == 36:
                self.add_status_code_to_output(FILE_NOT_FOUND)
            else:
                print(e)
        except Exception as e:
            print("Error interno del servidor\n")
            print(e)
            self.add_status_code_to_output(INTERNAL_ERROR)

    def get_slice(self, filename, offset, size):
        try:
            path_and_file = self.directory + filename
            file_size = path.getsize(path_and_file)

            # Chequea que el offset y size sean positivos y que su suma este
            # dentro del rango de lo que pesa el archivo
            if (offset >= 0 and size > 0 and ((offset + size) <= file_size)):
                fd = open(self.directory + filename, "rb")
                self.add_status_code_to_output(CODE_OK)

                # Creamos un generador para ir mandando el archivo en partes
                # por si el archivo es demasiado grande y no entra en memoria
                for piece in self.read_file_by_generator(fd, offset, size):
                    self.add_to_output(str(b64encode(piece), "ascii") + EOL)
                    self.send_data_to_client()
            else:
                self.add_status_code_to_output(BAD_OFFSET)

        except FileNotFoundError:
            self.add_status_code_to_output(FILE_NOT_FOUND)
        except OSError as e:
            # La excepcion captura cuando el filename es
            # demasiado largo (errno (error number) = 36)
            if e.errno == 36:
                self.add_status_code_to_output(FILE_NOT_FOUND)
            else:
                print(e)
        except Exception as e:
            print("Error interno del servidor\n")
            print(e)
            

    def quit(self):
        self.add_status_code_to_output(CODE_OK)
        self.connected = False

    def add_to_output(self, msg):
        self.output_buffer += msg

    def add_status_code_to_output(self, status_code):
        self.add_to_output(self.create_code_msg(status_code))
        if fatal_status(status_code):
            self.connected = False

    def create_code_msg(self, status_code):
        return (str(status_code) + " " + error_messages[status_code] + EOL)

    def read_file_by_generator(self, fd, offset, size):
        try:
            fd.seek(offset)
            chunk_size = 1024

            if(size < chunk_size):
                chunk_size = size

            sent = 0
            while (sent != size):
                if(chunk_size < size - sent):
                    chunk_size = size - sent

                data = fd.read(chunk_size)
                sent += chunk_size

                if not data:
                    break
                yield data
        except Exception as e:
            print("Error interno del servidor.\n")
            print(e)
            add_status_code_to_output(INTERNAL_ERROR)

    def send_data_to_client(self):
        try:
            # Mientras haya algo que enviar en el output_buffer sigue
            # enviando hasta que haya terminado
            while self.output_buffer:
                # Send devuelve cuantos bytes fueron enviados, porque puede
                # pasar que no se haya podido enviar todo lo que queriamos
                # por lo tanto guardamos la cantidad de bytes que fueron
                # enviados para quitarlos del output_buffer, y seguir enviando
                # los que no pudieron ser enviados mas los que quedan por
                # enviar
                bytes_sent = self.s.send(
                    self.output_buffer.encode("ascii"))
                self.output_buffer = self.output_buffer[bytes_sent:]
        except Exception as e:
            print("Fallo el envio de datos al cliente.\n")
            print(e)
            add_status_code_to_output(INTERNAL_ERROR)
            send_data_to_client()

    def is_connected(self):
        return self.connected
