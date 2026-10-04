"""
═══════════════════════════════════════════════════════════════
  SERVIDOR DE CHAT - Redes de Datos
  Servidor central TCP que gestiona múltiples clientes
  mediante hilos y retransmite mensajes en broadcast.
═══════════════════════════════════════════════════════════════
"""

import socket
import threading
import json
import sys
from datetime import datetime

# ─── Configuración ───────────────────────────────────────────
HOST = "0.0.0.0"        # Escuchar en todas las interfaces
PUERTO = 5050            # Puerto del servidor
BUFFER_SIZE = 4096       # Tamaño del buffer de recepción
CODIFICACION = "utf-8"

# ─── Estado global del servidor ──────────────────────────────
clientes = {}            # {socket_cliente: nombre_usuario}
lock = threading.Lock()  # Lock para acceso seguro a 'clientes'


def log(mensaje: str):
    """Imprime un mensaje con marca de tiempo en la consola del servidor."""
    hora = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"  [{hora}] {mensaje}")
    except UnicodeEncodeError:
        # Fallback para consolas Windows con codificación limitada
        print(f"  [{hora}] {mensaje.encode('ascii', 'replace').decode()}")


def enviar_mensaje(cliente_socket: socket.socket, tipo: str, **kwargs):
    """
    Envía un mensaje JSON al cliente especificado.
    Tipos: 'chat', 'sistema', 'lista', 'error', 'bienvenida'
    """
    datos = {"tipo": tipo, **kwargs}
    try:
        payload = json.dumps(datos, ensure_ascii=False) + "\n"
        cliente_socket.sendall(payload.encode(CODIFICACION))
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass  # El cliente ya se desconectó


def broadcast(tipo: str, remitente_socket=None, **kwargs):
    """
    Envía un mensaje a TODOS los clientes conectados.
    Si se proporciona remitente_socket, se excluye del broadcast.
    """
    with lock:
        destinatarios = list(clientes.keys())

    for cliente in destinatarios:
        if cliente != remitente_socket:
            enviar_mensaje(cliente, tipo, **kwargs)


def obtener_lista_usuarios() -> list:
    """Retorna la lista de nombres de usuarios conectados."""
    with lock:
        return list(clientes.values())


def desconectar_cliente(cliente_socket: socket.socket):
    """Desconecta a un cliente y notifica a los demás."""
    with lock:
        nombre = clientes.pop(cliente_socket, None)

    if nombre:
        log(f"[X] {nombre} se ha desconectado.")
        broadcast(
            "sistema",
            mensaje=f"{nombre} ha abandonado el chat.",
            usuarios=obtener_lista_usuarios(),
        )
    try:
        cliente_socket.close()
    except OSError:
        pass


def manejar_cliente(cliente_socket: socket.socket, direccion: tuple):
    """
    Hilo dedicado a un cliente: lee su nombre, procesa sus
    mensajes y ejecuta los comandos especiales.
    """
    nombre = None
    buffer = ""

    try:
        # ── Fase 1: Registro del usuario ─────────────────────
        while True:
            datos = cliente_socket.recv(BUFFER_SIZE)
            if not datos:
                cliente_socket.close()
                return
            buffer += datos.decode(CODIFICACION)
            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    msg = json.loads(linea)
                except json.JSONDecodeError:
                    continue

                if msg.get("tipo") == "registro":
                    nombre_propuesto = msg.get("nombre", "").strip()
                    if not nombre_propuesto:
                        enviar_mensaje(cliente_socket, "error",
                                       mensaje="El nombre no puede estar vacío.")
                        continue

                    # Verificar nombre duplicado
                    with lock:
                        if nombre_propuesto in clientes.values():
                            enviar_mensaje(cliente_socket, "error",
                                           mensaje=f"El nombre '{nombre_propuesto}' ya está en uso. Elige otro.")
                            continue
                        nombre = nombre_propuesto
                        clientes[cliente_socket] = nombre

                    log(f"[+] {nombre} se ha conectado desde {direccion[0]}:{direccion[1]}")

                    # Bienvenida al usuario
                    enviar_mensaje(
                        cliente_socket, "bienvenida",
                        mensaje=f"Bienvenido al chat, {nombre}!\n"
                                f"Comandos: /listar -> ver usuarios | /quitar -> salir",
                        usuarios=obtener_lista_usuarios(),
                    )

                    # Notificar a los demás
                    broadcast(
                        "sistema",
                        remitente_socket=cliente_socket,
                        mensaje=f"{nombre} se ha unido al chat.",
                        usuarios=obtener_lista_usuarios(),
                    )
                    break  # Salir del bucle de registro
            if nombre:
                break

        # ── Fase 2: Bucle de mensajes ────────────────────────
        while True:
            datos = cliente_socket.recv(BUFFER_SIZE)
            if not datos:
                break  # Desconexión limpia

            buffer += datos.decode(CODIFICACION)

            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    msg = json.loads(linea)
                except json.JSONDecodeError:
                    continue

                tipo_msg = msg.get("tipo", "")

                # ── Comando /listar ──────────────────────────
                if tipo_msg == "comando" and msg.get("comando") == "/listar":
                    usuarios = obtener_lista_usuarios()
                    enviar_mensaje(
                        cliente_socket, "lista",
                        mensaje=f"Usuarios conectados ({len(usuarios)}):",
                        usuarios=usuarios,
                    )

                # ── Comando /quitar ──────────────────────────
                elif tipo_msg == "comando" and msg.get("comando") == "/quitar":
                    enviar_mensaje(
                        cliente_socket, "sistema",
                        mensaje="Has salido del chat. Hasta pronto!",
                    )
                    break

                # ── Mensaje normal de chat ───────────────────
                elif tipo_msg == "chat":
                    contenido = msg.get("mensaje", "").strip()
                    if contenido:
                        hora = datetime.now().strftime("%H:%M")
                        log(f"[MSG] {nombre}: {contenido}")
                        broadcast(
                            "chat",
                            remitente_socket=cliente_socket,
                            remitente=nombre,
                            mensaje=contenido,
                            hora=hora,
                        )
                        # Eco al remitente con marca de "propio"
                        enviar_mensaje(
                            cliente_socket, "chat",
                            remitente=nombre,
                            mensaje=contenido,
                            hora=hora,
                            propio=True,
                        )

    except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
        log(f"[!] Conexion perdida con {nombre or direccion}: {e}")
    finally:
        desconectar_cliente(cliente_socket)


def iniciar_servidor():
    """Arranca el servidor TCP y acepta conexiones entrantes."""
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor_socket.bind((HOST, PUERTO))
    except OSError as e:
        print(f"\n  [ERROR] No se pudo iniciar el servidor en {HOST}:{PUERTO}")
        print(f"          {e}")
        sys.exit(1)

    servidor_socket.listen(10)

    print()
    print("  +===================================================+")
    print("  |          SERVIDOR DE CHAT ACTIVO                  |")
    print("  +===================================================+")
    print(f"  |  Direccion:  {HOST}:{PUERTO}                       |")
    print("  |  Esperando conexiones...                         |")
    print("  |  Presiona Ctrl+C para detener el servidor        |")
    print("  +===================================================+")
    print()

    try:
        while True:
            cliente_socket, direccion = servidor_socket.accept()
            hilo = threading.Thread(
                target=manejar_cliente,
                args=(cliente_socket, direccion),
                daemon=True,
            )
            hilo.start()
    except KeyboardInterrupt:
        print("\n\n  [STOP] Servidor detenido por el usuario.\n")
    finally:
        # Notificar a todos los clientes
        broadcast("sistema", mensaje="El servidor se esta cerrando.")
        with lock:
            for cliente in list(clientes.keys()):
                try:
                    cliente.close()
                except OSError:
                    pass
            clientes.clear()
        servidor_socket.close()


if __name__ == "__main__":
    iniciar_servidor()
