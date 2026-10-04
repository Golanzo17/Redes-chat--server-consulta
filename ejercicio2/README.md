# 🖥️ Ejercicio 2: Servidor de Consultas de Inventario HW/SW por Sockets

Sistema distribuido de auditoría e inventario de hardware y software basado en comunicación cliente-servidor mediante **Sockets TCP** en Python.

---

## Descripción del Sistema

Un **Servidor Central de Inventario** administra y audita múltiples máquinas en la red (locales o remotas). Cada máquina corre un **Agente Cliente** que recolecta en tiempo real métricas detalladas del sistema y responde a las peticiones del servidor.

### Métricas auditadas (según consigna):
1. **Características del Procesador (CPU)**: Modelo, arquitectura, núcleos físicos/lógicos, frecuencia en MHz.
2. **Memoria RAM**: Memoria total, usada, libre, porcentaje de uso (en MB y GB).
3. **Estado del Disco**: Espacio total, usado, libre y porcentaje de utilización por cada unidad/partición.
4. **Filesystem**: Tipos de sistema de archivos (NTFS, ext4, FAT32, etc.), puntos de montaje y particiones.
5. **Promedio de Carga (Load Average)**: Carga a 1, 5 y 15 minutos en Linux (`/proc/loadavg` o `os.getloadavg()`) y uso actual de CPU en Windows.
6. **Sistema Operativo y Hostname**: Nombre del equipo, distribución/versión del SO, release, kernel o build.
7. **Interfaces de Red**: Adaptadores físicos/virtuales, direcciones IPv4, estado de conexión.
8. **Procesos en Ejecución**: Total de procesos activos y tabla de procesos principales (PID, nombre, consumo).
9. **Inventario Completo y Exportación**: Genera una auditoría consolidada de toda la máquina y permite exportarla en formato JSON.

---

## 🌐 Compatibilidad Híbrida Multiplataforma

El agente cliente detecta automáticamente el sistema operativo y utiliza las fuentes nativas correspondientes **sin requerir librerías externas (`pip`)**:

| Métrica | En Linux (según consigna) | En Windows (pruebas locales) |
|---|---|---|
| **CPU** | Lectura de `/proc/cpuinfo` y `lscpu` | Registro de Windows y `platform.processor()` |
| **RAM** | Lectura de `/proc/meminfo` y comando `free` | API Win32 `GlobalMemoryStatusEx` |
| **Disco** | Comando `df -h` y `shutil.disk_usage` | Detección de unidades lógicas y `shutil` |
| **Filesystem** | `df -hT` y `/proc/partitions` | API Win32 `GetVolumeInformationW` (NTFS/FAT) |
| **Load Average** | `/proc/loadavg` y `os.getloadavg()` | Cálculo de CPU% con `GetSystemTimes` |
| **Sistema Operativo** | Comandos `hostnamectl`, `hostname`, `/proc/version` | `platform.platform()`, `platform.version()` |
| **Interfaces de Red** | Comando `ip address` y `/proc/net/dev` | Comando `ipconfig` y `socket.getaddrinfo` |
| **Procesos** | Comando `ps -eo pid,user,%cpu,%mem,comm` | Comando nativo `tasklist /FO CSV` |

---

## Cómo Ejecutar

### Opción 1: Con los archivos ejecutables (.bat)
1. **Iniciar el Servidor:** Haz doble clic en `Iniciar_Servidor_Inventario.bat`.
2. **Iniciar uno o más Agentes:** Haz doble clic en `Iniciar_Agente_Inventario.bat` (puedes abrir tantos agentes como desees, en la misma PC o en otras máquinas de la red).

### Opción 2: Desde la Terminal
1. En una terminal, arranca el servidor:
   ```bash
   python servidor_inventario.py
   ```
2. En otra terminal (o en otra máquina), arranca el agente:
   ```bash
   python cliente_agente.py
   ```
   *Ingresa la IP del servidor (127.0.0.1 para pruebas locales o la IP local 192.168.1.X para red LAN).*

---

## Panel de Control del Servidor

El servidor cuenta con un menú interactivo en consola:

```text
=================================================================
    PANEL DE CONTROL - SERVIDOR DE INVENTARIO HW/SW (TCP)
=================================================================
   [1]  Listar equipos / máquinas conectadas
   [2]  Consultar Procesador (CPU)
   [3]  Consultar Memoria RAM
   [4]  Consultar Estado de Discos
   [5]  Consultar Filesystem y Particiones
   [6]  Consultar Promedio de Carga (Load Average)
   [7]  Consultar Sistema Operativo y Hostname
   [8]  Consultar Interfaces de Red
   [9]  Consultar Procesos en Ejecución
   [10] Realizar Auditoría / Inventario COMPLETO
   [11] Exportar Inventario de una máquina a archivo (JSON)
   [0]  Salir del Servidor
-----------------------------------------------------------------
```

> **Consulta Individual o Masiva:** En cada opción puedes ingresar el **ID** de una máquina particular (ej: `1`) o ingresar **`T`** para consultar a **todas** las máquinas conectadas en simultáneo.

---

## Protocolo de Comunicación

- **Capa de Transporte:** TCP (`socket.SOCK_STREAM`), puerto `5051`.
- **Enmarcado (Framing):** Objetos JSON delimitados por salto de línea (`\n`).
- **Petición del Servidor:**
  ```json
  {"tipo": "consulta", "categoria": "cpu"}
  ```
- **Respuesta del Cliente:**
  ```json
  {
    "tipo": "respuesta_consulta",
    "categoria": "cpu",
    "hostname": "DESKTOP-7827F7N",
    "timestamp": "2026-10-04 04:49:08",
    "exito": true,
    "datos": {
      "modelo": "AMD Ryzen 5 2400G with Radeon Vega Graphics",
      "arquitectura": "AMD64",
      "nucleos_logicos": 8,
      "frecuencia_mhz": 3600
    }
  }
  ```
