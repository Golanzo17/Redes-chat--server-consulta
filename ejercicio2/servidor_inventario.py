"""
═══════════════════════════════════════════════════════════════
  SERVIDOR DE INVENTARIO HW/SW - Redes de Datos
  Ejercicio 2: Servidor central de auditoría y consultas por Sockets
  
  Gestiona conexiones de múltiples agentes clientes en red y
  permite consultar de forma individual o masiva las
  características de hardware y software (CPU, RAM, Discos,
  Filesystem, Load Average, SO, Red, Procesos).
═══════════════════════════════════════════════════════════════
"""

import socket
import threading
import json
import sys
import os
import time
from datetime import datetime

# Asegurar codificación UTF-8 en consolas Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Configuración ───────────────────────────────────────────
HOST = "0.0.0.0"          # Escuchar en todas las interfaces de red
PUERTO = 5051              # Puerto exclusivo para inventario
BUFFER_SIZE = 16384        # Buffer amplio para reportes grandes
CODIFICACION = "utf-8"

# ─── Estado del servidor ─────────────────────────────────────
# { cliente_id: { "socket": s, "direccion": (ip, port), "hostname": h, "sistema": so, "event": threading.Event(), "ultima_respuesta": dict } }
clientes = {}
contador_clientes = 0
lock = threading.Lock()


# ═════════════════════════════════════════════════════════════
# PROTOCOLO DE ENVÍO Y RECEPCIÓN
# ═════════════════════════════════════════════════════════════

def enviar_json(sock: socket.socket, datos: dict) -> bool:
    """Envía un diccionario serializado en JSON delimitado por '\\n'."""
    try:
        payload = json.dumps(datos, ensure_ascii=False) + "\n"
        sock.sendall(payload.encode(CODIFICACION))
        return True
    except (OSError, BrokenPipeError):
        return False


def atender_cliente(cliente_id: int, sock: socket.socket, direccion: tuple):
    """Hilo individual que escucha mensajes del cliente auditado."""
    buffer = ""
    try:
        while True:
            datos = sock.recv(BUFFER_SIZE)
            if not datos:
                break

            buffer += datos.decode(CODIFICACION)
            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                linea = linea.strip()
                if not linea:
                    continue

                try:
                    mensaje = json.loads(linea)
                except json.JSONDecodeError:
                    continue

                tipo = mensaje.get("tipo", "")

                if tipo == "registro":
                    with lock:
                        if cliente_id in clientes:
                            clientes[cliente_id]["hostname"] = mensaje.get("hostname", "Desconocido")
                            clientes[cliente_id]["sistema"] = mensaje.get("sistema", "Desconocido")
                            clientes[cliente_id]["release"] = mensaje.get("release", "")
                            clientes[cliente_id]["arquitectura"] = mensaje.get("arquitectura", "")
                    print(f"\n  [+] Nuevo equipo registrado: ID #{cliente_id} - {mensaje.get('hostname')} ({mensaje.get('sistema')}) desde {direccion[0]}")
                    print("  ➜ Presiona Enter para refrescar el menú...")

                elif tipo == "respuesta_consulta":
                    with lock:
                        if cliente_id in clientes:
                            clientes[cliente_id]["ultima_respuesta"] = mensaje
                            evento = clientes[cliente_id].get("evento")
                            if evento:
                                evento.set()

    except (ConnectionResetError, ConnectionAbortedError, OSError):
        pass
    finally:
        with lock:
            if cliente_id in clientes:
                host_desconectado = clientes[cliente_id].get("hostname", f"ID #{cliente_id}")
                del clientes[cliente_id]
                print(f"\n  [-] Equipo desconectado: {host_desconectado} ({direccion[0]})")
        try:
            sock.close()
        except OSError:
            pass


# ═════════════════════════════════════════════════════════════
# FORMATOS Y VISUALIZACIÓN DE AUDITORÍAS
# ═════════════════════════════════════════════════════════════

def imprimir_tabla_clientes():
    """Muestra los clientes/máquinas conectados actualmente."""
    with lock:
        items = list(clientes.items())

    print("\n  " + "═" * 70)
    print("   EQUIPOS CONECTADOS AL SERVIDOR DE INVENTARIO")
    print("  " + "═" * 70)
    if not items:
        print("   (No hay equipos conectados actualmente en espera)")
        print("   Inicia un agente ejecutando 'Iniciar_Agente.bat' en una terminal.")
        print("  " + "═" * 70)
        return

    print(f"   {'ID':<5} {'HOSTNAME':<22} {'SISTEMA OPERATIVO':<20} {'IP ORIGEN':<16}")
    print("  " + "─" * 70)
    for cid, info in items:
        h = info.get("hostname", "???")
        so = f"{info.get('sistema', '')} {info.get('release', '')}".strip()
        ip = info.get("direccion", ("?", "?"))[0]
        print(f"   #{cid:<4} {h:<22} {so:<20} {ip:<16}")
    print("  " + "═" * 70)


def mostrar_resultado_consulta(categoria: str, host: str, respuesta: dict):
    """Muestra en pantalla el resultado de la consulta formateado."""
    datos = respuesta.get("datos", {})
    ts = respuesta.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("\n  " + "═" * 72)
    print(f"   REPORTE DE AUDITORÍA: {categoria.upper()} | EQUIPO: {host}")
    print(f"   Marca de tiempo: {ts}")
    print("  " + "═" * 72)

    if categoria == "cpu":
        print(f"   • Modelo:             {datos.get('modelo', 'N/D')}")
        print(f"   • Arquitectura:       {datos.get('arquitectura', 'N/D')}")
        print(f"   • Núcleos Lógicos:    {datos.get('nucleos_logicos', 'N/D')}")
        if datos.get("nucleos_fisicos"):
            print(f"   • Núcleos Físicos:    {datos.get('nucleos_fisicos')}")
        if datos.get("frecuencia_mhz"):
            print(f"   • Frecuencia:         {datos.get('frecuencia_mhz')} MHz")
        print(f"   • Fuente de datos:    {datos.get('fuente', 'N/D')}")

    elif categoria == "ram":
        total = datos.get("total_mb", 0)
        usado = datos.get("usado_mb", 0)
        libre = datos.get("libre_mb", 0)
        porc = datos.get("porcentaje_uso", 0.0)
        barra = "█" * int(porc / 5) + "░" * (20 - int(porc / 5))

        print(f"   • RAM Total:          {total} MB ({round(total/1024, 2)} GB)")
        print(f"   • RAM en Uso:         {usado} MB ({round(usado/1024, 2)} GB)")
        print(f"   • RAM Libre/Disp.:    {libre} MB ({round(libre/1024, 2)} GB)")
        print(f"   • Porcentaje de Uso:  [{barra}] {porc}%")
        print(f"   • Fuente de datos:    {datos.get('fuente', 'N/D')}")

    elif categoria == "disco":
        discos = datos if isinstance(datos, list) else []
        if not discos:
            print("   (No se detectaron discos o información inaccesible)")
        else:
            print(f"   {'UNIDAD/DEV':<12} {'PUNTO MONTAJE':<16} {'TOTAL':<10} {'USADO':<10} {'LIBRE':<10} {'USO %':<8}")
            print("   " + "─" * 68)
            for d in discos:
                dev = d.get("dispositivo", "?")
                mnt = d.get("punto_montaje", "?")
                tot = d.get("total", "?")
                usd = d.get("usado", "?")
                lib = d.get("libre", "?")
                prc = d.get("porcentaje_uso", "?")
                print(f"   {dev:<12} {mnt:<16} {tot:<10} {usd:<10} {lib:<10} {prc:<8}")

    elif categoria == "filesystem":
        fs_list = datos if isinstance(datos, list) else []
        if not fs_list:
            print("   (No se detectaron sistemas de archivos)")
        else:
            print(f"   {'DISPOSITIVO':<12} {'TIPO FS':<12} {'ETIQUETA/INFO':<22} {'TAMAÑO':<10} {'DISPONIBLE':<10}")
            print("   " + "─" * 68)
            for f in fs_list:
                dev = f.get("dispositivo", "?")
                tfs = f.get("tipo_fs", "?")
                etiq = f.get("etiqueta_volumen", f.get("punto_montaje", "-"))
                tam = f.get("tamano", "?")
                disp = f.get("disponible", "?")
                print(f"   {dev:<12} {tfs:<12} {etiq:<22} {tam:<10} {disp:<10}")

    elif categoria == "loadavg":
        l1 = datos.get("load_1m")
        l5 = datos.get("load_5m")
        l15 = datos.get("load_15m")
        cpu_p = datos.get("cpu_uso_actual_porc")

        if l1 is not None:
            print(f"   • Carga Promedio (1 min):   {l1}")
        if l5 is not None:
            print(f"   • Carga Promedio (5 min):   {l5}")
        if l15 is not None:
            print(f"   • Carga Promedio (15 min):  {l15}")
        if cpu_p is not None:
            print(f"   • Uso de CPU Actual:        {cpu_p}%")
        print(f"   • Fuente de datos:          {datos.get('fuente', 'N/D')}")

    elif categoria == "so":
        print(f"   • Hostname:           {datos.get('hostname', 'N/D')}")
        print(f"   • Sistema Operativo:  {datos.get('sistema', 'N/D')}")
        print(f"   • Release / Versión:  {datos.get('release', 'N/D')} ({datos.get('version', 'N/D')})")
        print(f"   • Kernel o Build:     {datos.get('kernel_o_build', 'N/D')}")
        print(f"   • Arquitectura:       {datos.get('arquitectura', 'N/D')}")
        print(f"   • Fuente de datos:    {datos.get('fuente', 'N/D')}")

    elif categoria == "red":
        interfaces = datos if isinstance(datos, list) else []
        print(f"   {'INTERFAZ / ADAPTADOR':<35} {'DIRECCIÓN IP / DETALLES':<32}")
        print("   " + "─" * 68)
        for iface in interfaces:
            nom = iface.get("interfaz", "?")
            ip = iface.get("ipv4", iface.get("direcciones", iface.get("estado", "-")))
            print(f"   {nom[:33]:<35} {ip[:30]:<32}")

    elif categoria == "procesos":
        total_p = datos.get("total_procesos", 0)
        muestra = datos.get("muestra_procesos", [])
        print(f"   • Total de procesos activos: {total_p}")
        print(f"\n   {'PID':<8} {'NOMBRE PROCESO':<30} {'CONSUMO / SESIÓN':<25}")
        print("   " + "─" * 68)
        for proc in muestra:
            pid = str(proc.get("pid", "?"))
            nom = proc.get("nombre", "?")
            cons = proc.get("memoria", proc.get("cpu_porc", ""))
            print(f"   {pid:<8} {nom[:28]:<30} {cons:<25}")

    elif categoria == "inventario_completo":
        mostrar_resultado_consulta("so", host, {"datos": datos.get("so", {}), "timestamp": ts})
        mostrar_resultado_consulta("cpu", host, {"datos": datos.get("cpu", {}), "timestamp": ts})
        mostrar_resultado_consulta("ram", host, {"datos": datos.get("ram", {}), "timestamp": ts})
        mostrar_resultado_consulta("loadavg", host, {"datos": datos.get("loadavg", {}), "timestamp": ts})
        mostrar_resultado_consulta("disco", host, {"datos": datos.get("disco", []), "timestamp": ts})
        mostrar_resultado_consulta("filesystem", host, {"datos": datos.get("filesystem", []), "timestamp": ts})
        mostrar_resultado_consulta("red", host, {"datos": datos.get("red", []), "timestamp": ts})
        mostrar_resultado_consulta("procesos", host, {"datos": datos.get("procesos", {}), "timestamp": ts})

    print("  " + "═" * 72 + "\n")


# ═════════════════════════════════════════════════════════════
# GESTOR DE CONSULTAS A CLIENTES
# ═════════════════════════════════════════════════════════════

def consultar_cliente(cid: int, categoria: str) -> dict:
    """Envía la consulta al cliente específico y espera su respuesta con timeout."""
    with lock:
        if cid not in clientes:
            return {"exito": False, "error": f"El equipo #{cid} ya no está conectado."}
        cliente_info = clientes[cid]
        sock = cliente_info["socket"]
        evento = threading.Event()
        cliente_info["evento"] = evento
        cliente_info["ultima_respuesta"] = None

    peticion = {"tipo": "consulta", "categoria": categoria}
    if not enviar_json(sock, peticion):
        return {"exito": False, "error": "Fallo al enviar datos por el socket."}

    # Esperar respuesta hasta 8 segundos
    recibido = evento.wait(timeout=8.0)
    if not recibido:
        return {"exito": False, "error": "Tiempo de espera agotado (timeout): el cliente no respondió."}

    with lock:
        return clientes.get(cid, {}).get("ultima_respuesta", {"exito": False, "error": "Respuesta vacía"})


def exportar_inventario(cid: int):
    """Obtiene el inventario completo y lo guarda en un archivo JSON y TXT."""
    print(f"\n  [*] Consultando inventario completo al equipo #{cid}...")
    resp = consultar_cliente(cid, "inventario_completo")
    if not resp.get("exito"):
        print(f"  [✗] Error: {resp.get('error', 'Desconocido')}")
        return

    hostname = resp.get("hostname", f"cliente_{cid}")
    timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"inventario_{hostname}_{timestamp_archivo}.json"
    ruta_guardado = os.path.join(os.path.dirname(__file__), nombre_archivo)

    try:
        with open(ruta_guardado, "w", encoding="utf-8") as f:
            json.dump(resp, f, indent=4, ensure_ascii=False)
        print(f"  [✓] Inventario exportado exitosamente:")
        print(f"      {ruta_guardado}")
    except Exception as e:
        print(f"  [✗] No se pudo guardar el archivo: {e}")


# ═════════════════════════════════════════════════════════════
# INTERFAZ DE ADMINISTRACIÓN Y BUCLE PRINCIPAL
# ═════════════════════════════════════════════════════════════

def seleccionar_destino() -> list:
    """Solicita al operador si desea consultar a un equipo o a todos."""
    with lock:
        disponibles = list(clientes.keys())

    if not disponibles:
        print("\n  [!] No hay equipos conectados actualmente.")
        return []

    print("\n  Opciones de destino:")
    print("   • Ingresa el número de ID (ej. 1)")
    print("   • Ingresa 'T' o 'todos' para consultar a todas las máquinas")
    opcion = input("  ➜ Destino: ").strip().lower()

    if opcion in ("t", "todos", "*"):
        return disponibles
    elif opcion.isdigit() and int(opcion) in disponibles:
        return [int(opcion)]
    else:
        print("  [!] ID no válido o cliente no encontrado.")
        return []


def ejecutar_consulta_categoria(categoria: str):
    """Pide destino y ejecuta la consulta especificada."""
    destinos = seleccionar_destino()
    if not destinos:
        return

    for cid in destinos:
        with lock:
            host = clientes.get(cid, {}).get("hostname", f"ID #{cid}")
        print(f"\n  ➜ Consultando [{categoria.upper()}] en {host} (ID #{cid})...")
        resp = consultar_cliente(cid, categoria)
        if resp.get("exito"):
            mostrar_resultado_consulta(categoria, host, resp)
        else:
            print(f"  [✗] Falló la consulta en {host}: {resp.get('error')}")


def menu_interactivo():
    """Bucle del menú interactivo en consola para el administrador."""
    while True:
        print("\n" + "═" * 65)
        print("    PANEL DE CONTROL - SERVIDOR DE INVENTARIO HW/SW (TCP)")
        print("═" * 65)
        print("   [1]  Listar equipos / máquinas conectadas")
        print("   [2]  Consultar Procesador (CPU)")
        print("   [3]  Consultar Memoria RAM")
        print("   [4]  Consultar Estado de Discos")
        print("   [5]  Consultar Filesystem y Particiones")
        print("   [6]  Consultar Promedio de Carga (Load Average)")
        print("   [7]  Consultar Sistema Operativo y Hostname")
        print("   [8]  Consultar Interfaces de Red")
        print("   [9]  Consultar Procesos en Ejecución")
        print("   [10] Realizar Auditoría / Inventario COMPLETO")
        print("   [11] Exportar Inventario de una máquina a archivo (JSON)")
        print("   [0]  Salir del Servidor")
        print("─" * 65)

        op = input("  Selecciona una opción [0-11]: ").strip()

        if op == "1":
            imprimir_tabla_clientes()
        elif op == "2":
            ejecutar_consulta_categoria("cpu")
        elif op == "3":
            ejecutar_consulta_categoria("ram")
        elif op == "4":
            ejecutar_consulta_categoria("disco")
        elif op == "5":
            ejecutar_consulta_categoria("filesystem")
        elif op == "6":
            ejecutar_consulta_categoria("loadavg")
        elif op == "7":
            ejecutar_consulta_categoria("so")
        elif op == "8":
            ejecutar_consulta_categoria("red")
        elif op == "9":
            ejecutar_consulta_categoria("procesos")
        elif op == "10":
            ejecutar_consulta_categoria("inventario_completo")
        elif op == "11":
            destinos = seleccionar_destino()
            if destinos:
                exportar_inventario(destinos[0])
        elif op == "0":
            print("\n  Cerrando servidor de inventario...")
            break
        else:
            print("  [!] Opción inválida. Intenta nuevamente.")


def arrancar_socket_servidor():
    """Hilo que gestiona el socket pasivo y acepta conexiones de agentes."""
    global contador_clientes
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor_socket.bind((HOST, PUERTO))
        servidor_socket.listen(15)
    except OSError as e:
        print(f"\n  [ERROR FATAL] No se pudo vincular el puerto {PUERTO}: {e}")
        sys.exit(1)

    while True:
        try:
            cliente_sock, direccion = servidor_socket.accept()
            with lock:
                contador_clientes += 1
                cid = contador_clientes
                clientes[cid] = {
                    "socket": cliente_sock,
                    "direccion": direccion,
                    "hostname": "Conectando...",
                    "sistema": "",
                    "release": "",
                    "arquitectura": "",
                    "evento": None,
                    "ultima_respuesta": None
                }
            hilo = threading.Thread(
                target=atender_cliente,
                args=(cid, cliente_sock, direccion),
                daemon=True
            )
            hilo.start()
        except OSError:
            break


def main():
    print()
    print("  +===================================================+")
    print("  |     SERVIDOR DE INVENTARIO HW/SW ACTIVO           |")
    print("  +===================================================+")
    print(f"  |  Puerto de escucha TCP: {PUERTO}                      |")
    print(f"  |  Escuchando en:         {HOST} (Todas las interfaces)|")
    print("  +===================================================+")

    # Iniciar hilo de sockets en segundo plano
    hilo_servidor = threading.Thread(target=arrancar_socket_servidor, daemon=True)
    hilo_servidor.start()

    # Bucle del menú de consola interactivo
    menu_interactivo()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  [STOP] Servidor detenido por el usuario.\n")
