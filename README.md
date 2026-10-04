# 🖧 Chat en Red — Sockets TCP (Python)

Aplicación de chat en red con arquitectura **cliente-servidor** implementada con **sockets TCP** y una interfaz gráfica con **Tkinter**.

---

## Requisitos

- **Python 3.8+** (incluye `tkinter`, `socket`, `threading`, `json`)
- No requiere librerías externas.

---

## Cómo ejecutar

### Opción A: Doble clic (recomendado)

1. Doble clic en **`Iniciar Servidor.bat`** → se abre el servidor (no cerrar esa ventana)
2. Doble clic en **`Abrir Chat.bat`** → se abre un cliente
3. Doble clic en **`Abrir Chat.bat`** otra vez → se abre otro cliente
4. ¡Listo! Conectarse y chatear.

### Opción B: Desde la terminal

#### 1. Iniciar el servidor

```bash
python servidor.py
```

El servidor se inicia en `0.0.0.0:5050` (escucha en todas las interfaces de red).

#### 2. Iniciar los clientes

Abrir **dos o más** terminales y ejecutar en cada una:

```bash
python cliente.py
```

Se abrirá una ventana gráfica donde se debe configurar:

| Campo               | Valor por defecto | Descripción                            |
|---------------------|-------------------|----------------------------------------|
| Dirección servidor  | `127.0.0.1`       | IP del servidor (localhost para pruebas)|
| Puerto              | `5050`            | Puerto donde escucha el servidor       |
| Nombre de usuario   | *(vacío)*         | Nombre con el que aparecerás en el chat|

### 3. Conectar desde otra computadora

Para conectarse desde otra PC en la misma red local:

1. En la PC del servidor, buscar la IP local con `ipconfig` (Windows) o `ifconfig` (Linux/Mac)
2. En los clientes, poner esa IP en el campo "Dirección del servidor"

---

## Comandos disponibles

| Comando    | Descripción                              |
|------------|------------------------------------------|
| `/listar`  | Muestra la lista de usuarios conectados  |
| `/quitar`  | Se desconecta del servidor y vuelve al login |

---

## Arquitectura

```
┌─────────────┐     TCP      ┌──────────────────┐     TCP      ┌─────────────┐
│  Cliente A  │ ◄──────────► │   Servidor       │ ◄──────────► │  Cliente B  │
│  (Tkinter)  │              │  (Threading)     │              │  (Tkinter)  │
└─────────────┘              │                  │              └─────────────┘
                             │  - Broadcast     │
┌─────────────┐     TCP      │  - Gestión de    │
│  Cliente C  │ ◄──────────► │    usuarios      │
│  (Tkinter)  │              │  - Comandos      │
└─────────────┘              └──────────────────┘
```

### Protocolo de comunicación

Los mensajes se intercambian en formato **JSON** separados por `\n`:

```json
{"tipo": "registro", "nombre": "Juan"}
{"tipo": "chat", "mensaje": "Hola a todos!"}
{"tipo": "comando", "comando": "/listar"}
{"tipo": "sistema", "mensaje": "Juan se ha unido al chat.", "usuarios": ["Juan", "María"]}
```

---

## Estructura del proyecto

```
Redes/
├── Iniciar Servidor.bat   # Doble clic para abrir el servidor
├── Abrir Chat.bat         # Doble clic para abrir un cliente
├── servidor.py            # Servidor central TCP (multi-hilo)
├── cliente.py             # Cliente con interfaz gráfica Tkinter
└── README.md              # Este archivo
```

---

## Características implementadas

- [x] Comunicación en tiempo real entre múltiples usuarios
- [x] Interfaz gráfica con pantalla de login y chat
- [x] Nombres de usuario únicos (sin duplicados)
- [x] Broadcasting de mensajes a todos los clientes
- [x] Comando `/listar` para ver usuarios conectados
- [x] Comando `/quitar` para desconectarse
- [x] Panel lateral con usuarios en línea (actualización en tiempo real)
- [x] Manejo de errores de conexión y desconexión
- [x] Notificaciones al conectarse/desconectarse un usuario
- [x] Colores diferentes para cada usuario en el chat
- [x] Indicador de mensajes propios ("tú")
- [x] Reconexión (vuelve al login al desconectarse)
