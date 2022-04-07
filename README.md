#Informe lab2
#Estructuracion del servidor
El objeto Server, que se encarga de aceptar las conexiones lo hicimos en server.py, el trabajo que realiza es quedarse escuchando por nuevas conexiones, cuando ingresa un nuevo cliente se crea un objeto Connection y se inicia un hilo para que se encargue de manejar la conexión.
Ademas de esto, Server lleva una lista con todas las conexiones y sus hilos correspondientes y se fija si es que algun hilo esta parado, si esto sucede es que la conexión que le corresponde ya esta cerrada, entonces limpia las listas de objetos Connection y Threads.

La comunicación con los clientes ya conectados la realizan los objetos Connection, estos los definimos en el archivo connection.py, se van a encargar de parsear los requests que vayan entrando y de proveer los archivos o información requerida, entre otras cosas, de manera robusta y confiable utilizando una implementación del protocolo HFTP.

#Decisiones de diseño
Decidimos implementarlo multicliente con hilos ya que nos parecio que nos daba el mejor trade-off entre complejidad de la modificación al servidor y escalabilidad.

Decidimos hacer un metodo parse_request() que se encargue de realizar el parseo del request y extrayendo los posibles comandos valido que puedan llegar a entrar, depende el comando chequeamos que los parametros sean validos y recien le pasamos esos datos a los metodos que se encarguen de procesarlos. Otra alternativa hubiese sido hacer el parseo dentro de cada metodo que nos pidieron, pero nos parecio que quedaba mas prolijo de esta manera, de esa forma al metodo le pasamos datos validos y solamente se tiene que encargar de procesarlos, quedandonos metodos concisos.

Decidimos usar generadores para el envio de archivos muy grandes.

Modularizamos bastante para que quede un codigo mas conciso, por ejemplos:
- Creando metodos como ser "create_code_msg(self, status_code)" el cual le pasas el codigo de error y devuelve el correspondiente response respetando el protocolo HFTP

Creamos un metodo send_data_to_client() el cual llamamos en handle() que ademas de servir para enviar los datos luego de procesar un request lo utilizamos para cuando enviamos archivos mediante get_slice() para aprovechar el uso del generador, el cual va procesando el archivo pero por partes, y tenemos que ir enviando segun nos las va dando.


#Dificultades encontradas

* Entender como funciona el metodo split() para ir capturando los comandos de a 1 mientras llegan. 

* Otra dificultad que tuvimos fue a la hora de enviar archivos grandes ya que tuvimos que investigar que sucedia por detras cuando python itera sobre un archivo, descubrimos que si queremos enviar un archivo en pedazos y utilizamos un for, python primero carga todo el archivo para poder mandarlo por partes, esto no nos sirve si queremos enviar un archivo muy grande, como ser una pelicula de 8gb y solo tenemos 2 gb de ram, descubrimos que una forma de solucionar esto era utilizando algo llamado generadores, lo cual va cargando segun se va necesitando enviar los slices que el cliente nos pide.

* Entender como funciona base64 para que la informacion llegue como debe ser,
decidimos enviar y recibir las cantidades de datos siempre en un multiplo de 4.

#Preguntas
###¿Qué estrategias existen para poder implementar este mismo servidor pero con capacidad de atender ​múltiples clientes simultáneamente​? Investigue y responda brevemente qué cambios serían necesario en el diseño del código
####Hacer fork luego de aceptar una conexión entrante de un cliente nuevo

Este es el metodo mas facil de implementar pero es el que consume mas recursos de memoria (se redunda en datos cargados del proceso) y CPU (por la cantidad de context switching que se tienen que realizar).
Para implementarlo seria agregar simplemente que cada vez que entra una conexión hacer un fork del programa y asignarle la conexión.

####Utilizar hilos por cada conexión nueva entrante:

Dejar un proceso escuchando conexiones entrantes y luego crear un thread para cada cliente nuevo que se este queriendo conectar.
Este es el segundo metodo mas facil de implementar, aprovecha mas el CPU si tiene mas de 1 nucleo, tiene mas escalabilidad que solo haciendo forks, no consume tanta memoria al ser hilos (la memoria es compartida) y ademas se pueden compartir los datos en memoria entre hilos (aunque hay que tener cuidado con los posibles problemas de concurrencia que puedan ocurrir).
La principal contra que tiene es que hay que manejar los posibles problemas que nos pueda dar la concurrencia
Para implementarlo seria agregar que cree un hilo por cada conexión nueva en server.py, y verificar en connection.py si algun metodo puede traer problemas de concurrencia, modificandolas para que sean aptas para multithreading con alguna de las tecnicas que exiten hoy en dia (semaforos, spinlocks, etc).
Nosotros utilizamos esta estrategia y no encontramos que puedan ocurrir problemas de concurrencia, ya que los clientes solamente pueden descargar los archivos y no enviar.
Otra cosa que hay que hacer es manejar los hilos que vamos creando para no ir dejando hilos corriendo sin hacer nada ya que tienen conexiones cerradas, para esto utilizamos listas con las conexiones e hilos y las chequeamos cuando un nuevo cliente se conecta, si es que hay algun hilo parado lo removemos de la lista junto con la conexion que el mismo estaba manejando.


####Utilizar Polling

Simular concurrencia utilizando polling, el cual consiste en tener un conjunto de file descriptors (fd's), uno por cada cliente, y escuchar eventos que los mismos producen, diferentes eventos son:

POLLIN Hay información lista para ser leida en el fd
POLLPRI Hay información urgente para ser leida en el fd
POLLOUT El fd esta listo para que se pueda escribir en el, no va a bloquear el proceso
POLLERR Ocurrió un error
POLLHUP El cliente se desconectó
POLLNVAL Request invalido, el fd no esta abierto

Este es el metodo mas laborioso de implementar en cuestión de codigo, pero es el que mas eficientemente utiliza los recursos, tiene diferentes implementaciones, algunas de las mas conocidas son:
- Select
- Poll
- Epoll (linux)
- kqueue (Simil Epoll pero para FreeBSD, MacOSX)
- /dev/poll (Simil Epoll pero para Solaris)
- I/O Completion Ports - IOCP (Simil Epoll pero para Windows)

Para implementarlo en nuestro codigo deberiamos modificar server.py para que para cada conexión cree un file descriptor y los agregue al conjunto de fds, luego hacer que el server escuche los eventos que nos vayan tirando los fds, y actuar depende del evento que estemos escuchando, por ejemplo si se dispara un POLLIN leer la información que esta queriendo transmitir el cliente, o si es un POLLOUT enviar la respuesta al fd del cliente.
Ademas debemos manejar el envio de esos eventos dentro de cada objeto Connection.

###Pruebe ejecutar el servidor en una máquina del laboratorio, mientras utiliza el cliente desde otra, hacia la ip de la máquina servidor. ¿Qué diferencia hay si se corre el servidor desde la IP “localhost”, “127.0.0.1” o la ip “0.0.0.0”?

Si corremos el servidor en "localhost" es lo mismo que correrlo en "127.0.0.1" ya que esta IP es la que denota a localhost y es la direccion que se usa para conectarse en la misma maquina, por esto una maquina externa no se va a poder conectar.

Cuando el servidor escucha por conexiones en la dirección 0.0.0.0 significa que el servidor escuchará conexiones en todas las direcciones IP disponibles en la computadora. Por ejemplo, si el host donde corre el servidor tiene 2 direcciones como ser "192.168.1.146" *(IP del host dentro de la red local)* y "127.0.0.1" *(localhost)*, un cliente externo podrá conectarse utilizando "192.168.1.146" y otro cliente local *(dentro del mismo host)* podrá conectarse al servidor utilizando la IP local.