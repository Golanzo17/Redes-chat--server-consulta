"""
═══════════════════════════════════════════════════════════════
  CLIENTE AGENTE DE INVENTARIO HW/SW - Redes de Datos
  Ejercicio 2: Servidor/Cliente de auditoría e inventario por Sockets
  
  Recolecta características del sistema (CPU, RAM, Disco,
  Filesystem, Load Average, SO, Red, Procesos) y responde a las
  consultas del servidor de inventario central.
  
  Soporte Híbrido:
    - En Linux: Lee /proc (cpuinfo, meminfo, loadavg, partitions)
                y comandos nativos (hostnamectl, ip, free, ps).
    - En Windows: Utiliza APIs nativas (ctypes, platform, shutil,
                  tasklist, GetSystemTimes).
═══════════════════════════════════════════════════════════════
"""

import socket
import json
import sys
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime

# Asegurar codificación UTF-8 en consolas Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Configuración por defecto ───────────────────────────────
HOST_DEFAULT = "127.0.0.1"
PUERTO_DEFAULT = 5051
BUFFER_SIZE = 8192
CODIFICACION = "utf-8"

SISTEMA = platform.system()  # 'Linux', 'Windows', 'Darwin'


# ═════════════════════════════════════════════════════════════
# RECOLECCIÓN DE MÉTRICAS HW / SW
# ═════════════════════════════════════════════════════════════

def obtener_info_cpu() -> dict:
    """Recolecta características del procesador."""
    info = {
        "modelo": platform.processor() or "Desconocido",
        "arquitectura": platform.machine(),
        "nucleos_logicos": os.cpu_count() or 1,
        "nucleos_fisicos": None,
        "frecuencia_mhz": None,
        "fuente": ""
    }

    if SISTEMA == "Linux":
        try:
            # Lectura de /proc/cpuinfo (requerido por consigna)
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("model name"):
                            info["modelo"] = line.split(":", 1)[1].strip()
                        elif line.startswith("cpu MHz"):
                            info["frecuencia_mhz"] = round(float(line.split(":", 1)[1].strip()), 1)
                        elif line.startswith("cpu cores"):
                            info["nucleos_fisicos"] = int(line.split(":", 1)[1].strip())
                info["fuente"] = "/proc/cpuinfo"
        except Exception:
            pass

    elif SISTEMA == "Windows":
        try:
            # Consulta WMI o registro de Windows
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            nombre, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            mhz, _ = winreg.QueryValueEx(key, "~MHz")
            info["modelo"] = nombre.strip()
            info["frecuencia_mhz"] = mhz
            info["fuente"] = "Windows Registry / Hardware Description"
        except Exception:
            info["fuente"] = "platform.processor()"

    return info


def obtener_info_ram() -> dict:
    """Recolecta información de la memoria RAM."""
    info = {
        "total_mb": 0,
        "usado_mb": 0,
        "libre_mb": 0,
        "porcentaje_uso": 0.0,
        "fuente": ""
    }

    if SISTEMA == "Linux":
        try:
            # Lectura directa de /proc/meminfo
            if os.path.exists("/proc/meminfo"):
                mem = {}
                with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        partes = line.split(":")
                        if len(partes) == 2:
                            clave = partes[0].strip()
                            valor = partes[1].strip().split()[0]
                            mem[clave] = int(valor)

                total_kb = mem.get("MemTotal", 0)
                disponible_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
                usado_kb = total_kb - disponible_kb

                info["total_mb"] = round(total_kb / 1024, 1)
                info["libre_mb"] = round(disponible_kb / 1024, 1)
                info["usado_mb"] = round(usado_kb / 1024, 1)
                if total_kb > 0:
                    info["porcentaje_uso"] = round((usado_kb / total_kb) * 100, 1)
                info["fuente"] = "/proc/meminfo & comando 'free'"
        except Exception:
            pass

    elif SISTEMA == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            total_mb = stat.ullTotalPhys / (1024 * 1024)
            libre_mb = stat.ullAvailPhys / (1024 * 1024)
            usado_mb = total_mb - libre_mb

            info["total_mb"] = round(total_mb, 1)
            info["libre_mb"] = round(libre_mb, 1)
            info["usado_mb"] = round(usado_mb, 1)
            info["porcentaje_uso"] = float(stat.dwMemoryLoad)
            info["fuente"] = "Win32 GlobalMemoryStatusEx"
        except Exception:
            pass

    return info


def obtener_info_disco() -> list:
    """Recolecta el estado del almacenamiento en discos y unidades."""
    discos = []

    if SISTEMA == "Linux":
        try:
            # Comando df -h
            salida = subprocess.check_output(
                ["df", "-h", "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs"],
                text=True, stderr=subprocess.DEVNULL
            )
            lineas = salida.strip().split("\n")[1:]
            for l in lineas:
                partes = l.split()
                if len(partes) >= 6:
                    discos.append({
                        "dispositivo": partes[0],
                        "punto_montaje": partes[5],
                        "total": partes[1],
                        "usado": partes[2],
                        "libre": partes[3],
                        "porcentaje_uso": partes[4]
                    })
        except Exception:
            # Fallback con shutil
            try:
                du = shutil.disk_usage("/")
                discos.append({
                    "dispositivo": "/",
                    "punto_montaje": "/",
                    "total": f"{round(du.total / (1024**3), 1)} GB",
                    "usado": f"{round(du.used / (1024**3), 1)} GB",
                    "libre": f"{round(du.free / (1024**3), 1)} GB",
                    "porcentaje_uso": f"{round((du.used / du.total) * 100, 1)}%"
                })
            except Exception:
                pass

    elif SISTEMA == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            bitmask = kernel32.GetLogicalDrives()
            for letra in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    ruta = f"{letra}:\\"
                    try:
                        du = shutil.disk_usage(ruta)
                        discos.append({
                            "dispositivo": f"{letra}:",
                            "punto_montaje": ruta,
                            "total": f"{round(du.total / (1024**3), 1)} GB",
                            "usado": f"{round(du.used / (1024**3), 1)} GB",
                            "libre": f"{round(du.free / (1024**3), 1)} GB",
                            "porcentaje_uso": f"{round((du.used / du.total) * 100, 1)}%"
                        })
                    except (PermissionError, OSError):
                        pass
                bitmask >>= 1
        except Exception:
            pass

    return discos


def obtener_info_filesystem() -> list:
    """Recolecta sistemas de archivos (Filesystem) y particiones."""
    fs_list = []

    if SISTEMA == "Linux":
        try:
            # Comando df -hT y lectura de /proc/partitions
            salida = subprocess.check_output(
                ["df", "-hT", "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs"],
                text=True, stderr=subprocess.DEVNULL
            )
            lineas = salida.strip().split("\n")[1:]
            for l in lineas:
                partes = l.split()
                if len(partes) >= 7:
                    fs_list.append({
                        "dispositivo": partes[0],
                        "tipo_fs": partes[1],
                        "punto_montaje": partes[6],
                        "tamano": partes[2],
                        "disponible": partes[4]
                    })
        except Exception:
            pass

        # Leer /proc/partitions si existe
        if not fs_list and os.path.exists("/proc/partitions"):
            try:
                with open("/proc/partitions", "r") as f:
                    for line in f.readlines()[2:]:
                        p = line.split()
                        if len(p) == 4:
                            fs_list.append({
                                "dispositivo": f"/dev/{p[3]}",
                                "tipo_fs": "bloques",
                                "bloques": p[2],
                                "punto_montaje": "-"
                            })
            except Exception:
                pass

    elif SISTEMA == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            bitmask = kernel32.GetLogicalDrives()
            for letra in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    ruta = f"{letra}:\\"
                    vol_name = ctypes.create_unicode_buffer(260)
                    fs_name = ctypes.create_unicode_buffer(260)
                    ret = kernel32.GetVolumeInformationW(
                        ruta, vol_name, 260, None, None, None, fs_name, 260
                    )
                    if ret:
                        try:
                            du = shutil.disk_usage(ruta)
                            fs_list.append({
                                "dispositivo": f"{letra}:",
                                "tipo_fs": fs_name.value or "Desconocido",
                                "etiqueta_volumen": vol_name.value or "(Sin etiqueta)",
                                "punto_montaje": ruta,
                                "tamano": f"{round(du.total / (1024**3), 1)} GB",
                                "disponible": f"{round(du.free / (1024**3), 1)} GB"
                            })
                        except OSError:
                            pass
                bitmask >>= 1
        except Exception:
            pass

    return fs_list


def obtener_info_loadavg() -> dict:
    """Recolecta el promedio de carga del sistema (loadavg)."""
    resultado = {
        "load_1m": None,
        "load_5m": None,
        "load_15m": None,
        "cpu_uso_actual_porc": None,
        "fuente": ""
    }

    if hasattr(os, "getloadavg"):
        # Linux / Unix estándar
        try:
            l1, l5, l15 = os.getloadavg()
            resultado["load_1m"] = round(l1, 2)
            resultado["load_5m"] = round(l5, 2)
            resultado["load_15m"] = round(l15, 2)
            resultado["fuente"] = "os.getloadavg() & /proc/loadavg"
            return resultado
        except (OSError, AttributeError):
            pass

    if SISTEMA == "Linux" and os.path.exists("/proc/loadavg"):
        try:
            with open("/proc/loadavg", "r") as f:
                partes = f.read().split()
                resultado["load_1m"] = float(partes[0])
                resultado["load_5m"] = float(partes[1])
                resultado["load_15m"] = float(partes[2])
                resultado["fuente"] = "/proc/loadavg"
                return resultado
        except Exception:
            pass

    if SISTEMA == "Windows":
        # En Windows calculamos el porcentaje de uso de CPU vía GetSystemTimes
        try:
            import ctypes
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

            def to_int(ft):
                return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

            i1, k1, u1 = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i1), ctypes.byref(k1), ctypes.byref(u1))
            time.sleep(0.12)
            i2, k2, u2 = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i2), ctypes.byref(k2), ctypes.byref(u2))

            idle = to_int(i2) - to_int(i1)
            kernel = to_int(k2) - to_int(k1)
            user = to_int(u2) - to_int(u1)
            total = kernel + user

            if total > 0:
                uso = round((1.0 - idle / total) * 100, 1)
                resultado["cpu_uso_actual_porc"] = uso
                # Estimación referencial
                resultado["load_1m"] = round((uso / 100) * (os.cpu_count() or 1), 2)
                resultado["fuente"] = "Win32 GetSystemTimes (CPU % instantáneo)"
        except Exception:
            pass

    return resultado


def obtener_info_so() -> dict:
    """Recolecta la versión del Sistema Operativo, Hostname y Uptime."""
    hostname = socket.gethostname()
    so_info = {
        "hostname": hostname,
        "sistema": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "arquitectura": platform.machine(),
        "kernel_o_build": "",
        "fuente": ""
    }

    if SISTEMA == "Linux":
        try:
            # Comando hostnamectl
            salida = subprocess.check_output(["hostnamectl"], text=True, stderr=subprocess.DEVNULL)
            for linea in salida.splitlines():
                if "Operating System:" in linea:
                    so_info["sistema"] = linea.split(":", 1)[1].strip()
                elif "Kernel:" in linea:
                    so_info["kernel_o_build"] = linea.split(":", 1)[1].strip()
            so_info["fuente"] = "comando 'hostnamectl' y 'hostname'"
        except Exception:
            # Fallback a /proc/version
            if os.path.exists("/proc/version"):
                try:
                    with open("/proc/version", "r") as f:
                        so_info["kernel_o_build"] = f.read().strip()
                        so_info["fuente"] = "/proc/version"
                except Exception:
                    pass

    elif SISTEMA == "Windows":
        so_info["sistema"] = f"Windows {platform.release()}"
        so_info["kernel_o_build"] = f"Build {platform.version()}"
        so_info["fuente"] = "platform.platform() / Windows API"

    return so_info


def obtener_info_red() -> list:
    """Recolecta interfaces de red y direcciones IP."""
    interfaces = []
    hostname = socket.gethostname()

    # IP local básica
    try:
        ip_local = socket.gethostbyname(hostname)
        interfaces.append({
            "interfaz": "Primaria (Hostname)",
            "ipv4": ip_local,
            "tipo": "Default"
        })
    except Exception:
        pass

    if SISTEMA == "Linux":
        try:
            # Comando 'ip address' o 'ip -br a' (pedido en consigna)
            salida = subprocess.check_output(["ip", "-br", "a"], text=True, stderr=subprocess.DEVNULL)
            for l in salida.strip().splitlines():
                p = l.split()
                if len(p) >= 2:
                    iface = p[0]
                    estado = p[1]
                    ips = p[2:] if len(p) > 2 else []
                    interfaces.append({
                        "interfaz": iface,
                        "estado": estado,
                        "direcciones": ", ".join(ips)
                    })
        except Exception:
            # Fallback /proc/net/dev
            if os.path.exists("/proc/net/dev"):
                try:
                    with open("/proc/net/dev", "r") as f:
                        for l in f.readlines()[2:]:
                            iface = l.split(":")[0].strip()
                            interfaces.append({"interfaz": iface, "fuente": "/proc/net/dev"})
                except Exception:
                    pass

    elif SISTEMA == "Windows":
        try:
            salida = subprocess.check_output(["ipconfig"], text=True, stderr=subprocess.DEVNULL)
            adaptador_actual = None
            for linea in salida.splitlines():
                l = linea.strip()
                if "Adaptador" in l or "adapter" in l.lower():
                    adaptador_actual = l.rstrip(":")
                elif "IPv4" in l and adaptador_actual:
                    partes = l.split(":")
                    if len(partes) >= 2:
                        ip = partes[1].strip().replace("(Preferido)", "").strip()
                        interfaces.append({
                            "interfaz": adaptador_actual,
                            "ipv4": ip,
                            "tipo": "Adaptador Windows"
                        })
        except Exception:
            pass

    return interfaces


def obtener_info_procesos(limite: int = 15) -> dict:
    """Recolecta procesos en ejecución (simulando o ejecutando 'ps' / 'tasklist')."""
    procesos = []
    total_procesos = 0

    if SISTEMA == "Linux":
        try:
            # Comando ps (solicitado en la consigna)
            salida = subprocess.check_output(
                ["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"],
                text=True, stderr=subprocess.DEVNULL
            )
            lineas = salida.strip().splitlines()
            total_procesos = max(0, len(lineas) - 1)
            for l in lineas[1:limite + 1]:
                p = l.split(None, 4)
                if len(p) >= 5:
                    procesos.append({
                        "pid": p[0],
                        "usuario": p[1],
                        "cpu_porc": p[2] + "%",
                        "mem_porc": p[3] + "%",
                        "nombre": p[4]
                    })
        except Exception:
            pass

    elif SISTEMA == "Windows":
        try:
            salida = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                text=True, stderr=subprocess.DEVNULL
            )
            lineas = [l for l in salida.strip().splitlines() if l.strip()]
            total_procesos = len(lineas)
            for l in lineas[:limite]:
                partes = [p.strip(' "') for p in l.split('","')]
                if len(partes) >= 5:
                    procesos.append({
                        "pid": partes[1],
                        "nombre": partes[0],
                        "sesion": partes[2],
                        "memoria": partes[4]
                    })
        except Exception:
            pass

    return {
        "total_procesos": total_procesos,
        "muestra_procesos": procesos
    }


def obtener_inventario_completo() -> dict:
    """Recolecta TODO el inventario del sistema de forma consolidada."""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "so": obtener_info_so(),
        "cpu": obtener_info_cpu(),
        "ram": obtener_info_ram(),
        "loadavg": obtener_info_loadavg(),
        "disco": obtener_info_disco(),
        "filesystem": obtener_info_filesystem(),
        "red": obtener_info_red(),
        "procesos": obtener_info_procesos(limite=10)
    }


# ═════════════════════════════════════════════════════════════
# COMUNICACIÓN DEL AGENTE CLIENTE VÍA SOCKETS
# ═════════════════════════════════════════════════════════════

class ClienteAgente:
    def __init__(self, host: str = HOST_DEFAULT, puerto: int = PUERTO_DEFAULT):
        self.host = host
        self.puerto = puerto
        self.sock = None
        self.conectado = False

    def conectar(self) -> bool:
        """Establece la conexión TCP con el servidor de inventario."""
        print()
        print("  ═══════════════════════════════════════════════════════════")
        print("    AGENTE DE INVENTARIO HW/SW - CLIENTE")
        print("  ═══════════════════════════════════════════════════════════")
        print(f"  • Sistema Operativo detectado: {SISTEMA} ({platform.release()})")
        print(f"  • Hostname local:              {socket.gethostname()}")
        print(f"  • Conectando a servidor:        {self.host}:{self.puerto}")
        print("  ───────────────────────────────────────────────────────────")

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(6)
            self.sock.connect((self.host, self.puerto))
            self.sock.settimeout(None)
            self.conectado = True
            print("  [✓] Conexión establecida exitosamente con el servidor.")
        except Exception as e:
            print(f"  [✗] Error al conectar con el servidor {self.host}:{self.puerto}")
            print(f"      Detalle: {e}")
            return False

        # Enviar registro inicial
        datos_registro = {
            "tipo": "registro",
            "hostname": socket.gethostname(),
            "sistema": SISTEMA,
            "release": platform.release(),
            "arquitectura": platform.machine(),
            "nucleos": os.cpu_count() or 1
        }
        self.enviar_json(datos_registro)
        print("  [✓] Registro enviado al servidor central.")
        print("  [*] En espera de consultas del servidor de inventario...")
        print("  ───────────────────────────────────────────────────────────")
        return True

    def enviar_json(self, datos: dict):
        """Envía un paquete JSON delimitado por salto de línea (\n)."""
        try:
            payload = json.dumps(datos, ensure_ascii=False) + "\n"
            self.sock.sendall(payload.encode(CODIFICACION))
        except (OSError, BrokenPipeError) as e:
            print(f"  [!] Error al transmitir datos: {e}")
            self.conectado = False

    def procesar_consulta(self, categoria: str) -> dict:
        """Ejecuta la recolección solicitada por el servidor."""
        hora = datetime.now().strftime("%H:%M:%S")
        print(f"  [{hora}] ➜ Consulta recibida del servidor: [{categoria.upper()}]")

        if categoria == "cpu":
            return {"exito": True, "datos": obtener_info_cpu()}
        elif categoria == "ram":
            return {"exito": True, "datos": obtener_info_ram()}
        elif categoria == "disco":
            return {"exito": True, "datos": obtener_info_disco()}
        elif categoria == "filesystem":
            return {"exito": True, "datos": obtener_info_filesystem()}
        elif categoria == "loadavg":
            return {"exito": True, "datos": obtener_info_loadavg()}
        elif categoria == "so":
            return {"exito": True, "datos": obtener_info_so()}
        elif categoria == "red":
            return {"exito": True, "datos": obtener_info_red()}
        elif categoria == "procesos":
            return {"exito": True, "datos": obtener_info_procesos()}
        elif categoria == "inventario_completo":
            return {"exito": True, "datos": obtener_inventario_completo()}
        else:
            return {"exito": False, "error": f"Categoría desconocida: {categoria}"}

    def bucle_escucha(self):
        """Escucha consultas continuas del servidor."""
        buffer = ""
        try:
            while self.conectado:
                datos = self.sock.recv(BUFFER_SIZE)
                if not datos:
                    print("\n  [!] El servidor cerró la conexión.")
                    break

                buffer += datos.decode(CODIFICACION)
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    linea = linea.strip()
                    if not linea:
                        continue
                    try:
                        peticion = json.loads(linea)
                    except json.JSONDecodeError:
                        continue

                    tipo = peticion.get("tipo", "")
                    if tipo == "consulta":
                        cat = peticion.get("categoria", "")
                        respuesta = self.procesar_consulta(cat)
                        paquete_respuesta = {
                            "tipo": "respuesta_consulta",
                            "categoria": cat,
                            "hostname": socket.gethostname(),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **respuesta
                        }
                        self.enviar_json(paquete_respuesta)
                        print(f"       ✔ Respuesta de [{cat.upper()}] transmitida al servidor.")

                    elif tipo == "ping":
                        self.enviar_json({"tipo": "pong"})

        except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
            print(f"\n  [!] Conexión interrumpida con el servidor: {e}")
        finally:
            self.desconectar()

    def desconectar(self):
        self.conectado = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        print("  [*] Agente finalizado. Presiona Enter para salir.")


# ═════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═════════════════════════════════════════════════════════════

def main():
    print()
    print("  =======================================================")
    print("     CONFIGURACIÓN DEL AGENTE CLIENTE (INVENTARIO)       ")
    print("  =======================================================")

    host = input(f"  Dirección IP del Servidor [por defecto {HOST_DEFAULT}]: ").strip()
    if not host:
        host = HOST_DEFAULT

    puerto_str = input(f"  Puerto del Servidor [por defecto {PUERTO_DEFAULT}]: ").strip()
    puerto = int(puerto_str) if puerto_str.isdigit() else PUERTO_DEFAULT

    agente = ClienteAgente(host, puerto)
    if agente.conectar():
        agente.bucle_escucha()
    else:
        input("\n  Presiona Enter para cerrar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  [STOP] Agente detenido manualmente por el usuario.\n")
