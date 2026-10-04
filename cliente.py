"""
═══════════════════════════════════════════════════════════════
  CLIENTE DE CHAT - Redes de Datos
  Cliente con interfaz gráfica (Tkinter) que se conecta
  al servidor de chat mediante sockets TCP.
═══════════════════════════════════════════════════════════════
"""

import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox
import sys

# ─── Configuración ───────────────────────────────────────────
BUFFER_SIZE = 4096
CODIFICACION = "utf-8"

# ─── Paleta de colores ───────────────────────────────────────
COLORES = {
    "fondo":          "#1a1a2e",
    "panel":          "#16213e",
    "panel_claro":    "#1e2d4a",
    "acento":         "#0f3460",
    "boton":          "#e94560",
    "boton_hover":    "#ff6b6b",
    "texto":          "#eaeaea",
    "texto_tenue":    "#8892b0",
    "texto_sistema":  "#64ffda",
    "msg_propio_bg":  "#0f3460",
    "msg_otro_bg":    "#16213e",
    "entrada_bg":     "#0d1b2a",
    "entrada_fg":     "#eaeaea",
    "borde":          "#233554",
    "online":         "#64ffda",
    "titulo":         "#ccd6f6",
}

# Colores para distinguir usuarios diferentes
COLORES_USUARIOS = [
    "#ff6b6b", "#ffd93d", "#6bcb77", "#4d96ff",
    "#ff8fab", "#c9b1ff", "#00d2ff", "#ff9e43",
    "#a8e6cf", "#dcedc1", "#ffd3b6", "#ffaaa5",
]


class ClienteChat:
    """Clase principal del cliente de chat con interfaz gráfica."""

    def __init__(self):
        self.socket_cliente = None
        self.conectado = False
        self.nombre_usuario = ""
        self.usuarios_conectados = []
        self.mapa_colores_usuario = {}
        self.indice_color = 0
        self.hilo_recepcion = None

        # ── Ventana principal ────────────────────────────────
        self.raiz = tk.Tk()
        self.raiz.title("💬 Chat en Red")
        self.raiz.geometry("900x650")
        self.raiz.minsize(750, 550)
        self.raiz.configure(bg=COLORES["fondo"])
        self.raiz.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        # Centrar ventana
        self.raiz.update_idletasks()
        ancho = self.raiz.winfo_width()
        alto = self.raiz.winfo_height()
        x = (self.raiz.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.raiz.winfo_screenheight() // 2) - (alto // 2)
        self.raiz.geometry(f"+{x}+{y}")

        self._crear_pantalla_login()

    # ═════════════════════════════════════════════════════════
    # PANTALLA DE LOGIN
    # ═════════════════════════════════════════════════════════

    def _crear_pantalla_login(self):
        """Crea la pantalla de inicio de sesión."""
        self.frame_login = tk.Frame(self.raiz, bg=COLORES["fondo"])
        self.frame_login.pack(expand=True, fill="both")

        # Contenedor central
        centro = tk.Frame(self.frame_login, bg=COLORES["panel"],
                          highlightbackground=COLORES["borde"],
                          highlightthickness=1, padx=40, pady=40)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        # Título
        tk.Label(centro, text="🖧", font=("Segoe UI Emoji", 48),
                 bg=COLORES["panel"], fg=COLORES["boton"]).pack(pady=(0, 5))
        tk.Label(centro, text="Chat en Red", font=("Segoe UI", 24, "bold"),
                 bg=COLORES["panel"], fg=COLORES["titulo"]).pack()
        tk.Label(centro, text="Redes de Datos — Sockets TCP",
                 font=("Segoe UI", 10),
                 bg=COLORES["panel"], fg=COLORES["texto_tenue"]).pack(pady=(2, 25))

        # Campo: Dirección del servidor
        tk.Label(centro, text="DIRECCIÓN DEL SERVIDOR",
                 font=("Segoe UI", 9, "bold"),
                 bg=COLORES["panel"], fg=COLORES["texto_tenue"],
                 anchor="w").pack(fill="x")
        self.entrada_host = tk.Entry(
            centro, font=("Consolas", 12),
            bg=COLORES["entrada_bg"], fg=COLORES["entrada_fg"],
            insertbackground=COLORES["texto"],
            highlightbackground=COLORES["borde"], highlightthickness=1,
            relief="flat", width=30,
        )
        self.entrada_host.insert(0, "127.0.0.1")
        self.entrada_host.pack(pady=(3, 12), ipady=6)

        # Campo: Puerto
        tk.Label(centro, text="PUERTO",
                 font=("Segoe UI", 9, "bold"),
                 bg=COLORES["panel"], fg=COLORES["texto_tenue"],
                 anchor="w").pack(fill="x")
        self.entrada_puerto = tk.Entry(
            centro, font=("Consolas", 12),
            bg=COLORES["entrada_bg"], fg=COLORES["entrada_fg"],
            insertbackground=COLORES["texto"],
            highlightbackground=COLORES["borde"], highlightthickness=1,
            relief="flat", width=30,
        )
        self.entrada_puerto.insert(0, "5050")
        self.entrada_puerto.pack(pady=(3, 12), ipady=6)

        # Campo: Nombre de usuario
        tk.Label(centro, text="NOMBRE DE USUARIO",
                 font=("Segoe UI", 9, "bold"),
                 bg=COLORES["panel"], fg=COLORES["texto_tenue"],
                 anchor="w").pack(fill="x")
        self.entrada_nombre = tk.Entry(
            centro, font=("Consolas", 12),
            bg=COLORES["entrada_bg"], fg=COLORES["entrada_fg"],
            insertbackground=COLORES["texto"],
            highlightbackground=COLORES["borde"], highlightthickness=1,
            relief="flat", width=30,
        )
        self.entrada_nombre.pack(pady=(3, 20), ipady=6)
        self.entrada_nombre.focus_set()
        self.entrada_nombre.bind("<Return>", lambda e: self.conectar())

        # Botón Conectar
        self.boton_conectar = tk.Button(
            centro, text="🔗  Conectar al chat",
            font=("Segoe UI", 12, "bold"),
            bg=COLORES["boton"], fg="white",
            activebackground=COLORES["boton_hover"], activeforeground="white",
            relief="flat", cursor="hand2", padx=20, pady=8,
            command=self.conectar,
        )
        self.boton_conectar.pack(pady=(0, 10))
        self.boton_conectar.bind("<Enter>",
            lambda e: self.boton_conectar.configure(bg=COLORES["boton_hover"]))
        self.boton_conectar.bind("<Leave>",
            lambda e: self.boton_conectar.configure(bg=COLORES["boton"]))

        # Label de estado
        self.label_estado_login = tk.Label(
            centro, text="", font=("Segoe UI", 9),
            bg=COLORES["panel"], fg=COLORES["boton"],
        )
        self.label_estado_login.pack()

    # ═════════════════════════════════════════════════════════
    # PANTALLA DE CHAT
    # ═════════════════════════════════════════════════════════

    def _crear_pantalla_chat(self):
        """Crea la interfaz principal del chat."""
        self.frame_chat = tk.Frame(self.raiz, bg=COLORES["fondo"])
        self.frame_chat.pack(expand=True, fill="both")

        # ── Barra superior ───────────────────────────────────
        barra = tk.Frame(self.frame_chat, bg=COLORES["acento"], height=50)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        tk.Label(barra, text="💬", font=("Segoe UI Emoji", 18),
                 bg=COLORES["acento"], fg="white").pack(side="left", padx=(15, 5))
        tk.Label(barra, text="Chat en Red",
                 font=("Segoe UI", 14, "bold"),
                 bg=COLORES["acento"], fg="white").pack(side="left")

        self.label_estado = tk.Label(
            barra, text=f"  ●  {self.nombre_usuario}",
            font=("Segoe UI", 10),
            bg=COLORES["acento"], fg=COLORES["online"],
        )
        self.label_estado.pack(side="left", padx=10)

        btn_desconectar = tk.Button(
            barra, text="Salir", font=("Segoe UI", 10),
            bg=COLORES["boton"], fg="white",
            activebackground=COLORES["boton_hover"],
            relief="flat", cursor="hand2", padx=10,
            command=self.desconectar,
        )
        btn_desconectar.pack(side="right", padx=15, pady=10)

        # ── Contenido principal ──────────────────────────────
        contenido = tk.Frame(self.frame_chat, bg=COLORES["fondo"])
        contenido.pack(expand=True, fill="both", padx=8, pady=(8, 0))

        # Panel izquierdo: mensajes
        panel_msgs = tk.Frame(contenido, bg=COLORES["panel"],
                              highlightbackground=COLORES["borde"],
                              highlightthickness=1)
        panel_msgs.pack(side="left", expand=True, fill="both", padx=(0, 4))

        # Área de mensajes con scrollbar
        frame_scroll = tk.Frame(panel_msgs, bg=COLORES["panel"])
        frame_scroll.pack(expand=True, fill="both", padx=2, pady=2)

        self.scrollbar = tk.Scrollbar(frame_scroll, bg=COLORES["panel_claro"],
                                       troughcolor=COLORES["panel"])
        self.scrollbar.pack(side="right", fill="y")

        self.area_mensajes = tk.Text(
            frame_scroll, font=("Consolas", 11),
            bg=COLORES["panel"], fg=COLORES["texto"],
            wrap="word", state="disabled",
            yscrollcommand=self.scrollbar.set,
            relief="flat", padx=12, pady=8,
            selectbackground=COLORES["acento"],
            cursor="arrow",
        )
        self.area_mensajes.pack(expand=True, fill="both")
        self.scrollbar.config(command=self.area_mensajes.yview)

        # Configurar tags para estilos de texto
        self.area_mensajes.tag_configure("sistema",
            foreground=COLORES["texto_sistema"], font=("Consolas", 10, "italic"))
        self.area_mensajes.tag_configure("error",
            foreground=COLORES["boton"], font=("Consolas", 10, "bold"))
        self.area_mensajes.tag_configure("hora",
            foreground=COLORES["texto_tenue"], font=("Consolas", 9))
        self.area_mensajes.tag_configure("propio_nombre",
            foreground=COLORES["online"], font=("Consolas", 11, "bold"))
        self.area_mensajes.tag_configure("propio_msg",
            foreground="#eaeaea", font=("Consolas", 11))
        self.area_mensajes.tag_configure("lista_titulo",
            foreground=COLORES["online"], font=("Consolas", 11, "bold"))
        self.area_mensajes.tag_configure("lista_item",
            foreground=COLORES["texto"], font=("Consolas", 10))

        # Panel derecho: usuarios conectados
        panel_usuarios = tk.Frame(contenido, bg=COLORES["panel"],
                                   highlightbackground=COLORES["borde"],
                                   highlightthickness=1, width=200)
        panel_usuarios.pack(side="right", fill="y", padx=(4, 0))
        panel_usuarios.pack_propagate(False)

        tk.Label(panel_usuarios, text="Usuarios en línea",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORES["panel"], fg=COLORES["titulo"],
                 anchor="w").pack(fill="x", padx=10, pady=(10, 5))

        separador = tk.Frame(panel_usuarios, bg=COLORES["borde"], height=1)
        separador.pack(fill="x", padx=10)

        self.lista_usuarios = tk.Listbox(
            panel_usuarios, font=("Consolas", 11),
            bg=COLORES["panel"], fg=COLORES["online"],
            selectbackground=COLORES["acento"],
            relief="flat", highlightthickness=0, bd=0,
            activestyle="none",
        )
        self.lista_usuarios.pack(expand=True, fill="both", padx=10, pady=8)

        self.label_conteo = tk.Label(
            panel_usuarios, text="0 conectados",
            font=("Segoe UI", 9),
            bg=COLORES["panel"], fg=COLORES["texto_tenue"],
        )
        self.label_conteo.pack(pady=(0, 10))

        # ── Barra de entrada de mensajes ─────────────────────
        barra_entrada = tk.Frame(self.frame_chat, bg=COLORES["panel"],
                                  highlightbackground=COLORES["borde"],
                                  highlightthickness=1)
        barra_entrada.pack(fill="x", padx=8, pady=8)

        self.entrada_mensaje = tk.Entry(
            barra_entrada, font=("Consolas", 12),
            bg=COLORES["entrada_bg"], fg=COLORES["entrada_fg"],
            insertbackground=COLORES["texto"],
            relief="flat",
        )
        self.entrada_mensaje.pack(side="left", expand=True, fill="both",
                                   padx=(8, 4), pady=8, ipady=6)
        self.entrada_mensaje.bind("<Return>", lambda e: self.enviar_mensaje())
        self.entrada_mensaje.focus_set()

        self.boton_enviar = tk.Button(
            barra_entrada, text="Enviar  ➤",
            font=("Segoe UI", 11, "bold"),
            bg=COLORES["boton"], fg="white",
            activebackground=COLORES["boton_hover"],
            relief="flat", cursor="hand2", padx=18,
            command=self.enviar_mensaje,
        )
        self.boton_enviar.pack(side="right", padx=(4, 8), pady=8)
        self.boton_enviar.bind("<Enter>",
            lambda e: self.boton_enviar.configure(bg=COLORES["boton_hover"]))
        self.boton_enviar.bind("<Leave>",
            lambda e: self.boton_enviar.configure(bg=COLORES["boton"]))

        # ── Barra de comandos (ayuda) ────────────────────────
        barra_cmds = tk.Frame(self.frame_chat, bg=COLORES["fondo"])
        barra_cmds.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(barra_cmds,
                 text="Comandos:  /listar → ver usuarios  │  /quitar → desconectarse",
                 font=("Consolas", 9),
                 bg=COLORES["fondo"], fg=COLORES["texto_tenue"],
                 ).pack(side="left")

    # ═════════════════════════════════════════════════════════
    # CONEXIÓN Y RED
    # ═════════════════════════════════════════════════════════

    def conectar(self):
        """Intenta conectarse al servidor y registrar el nombre de usuario."""
        host = self.entrada_host.get().strip()
        puerto_str = self.entrada_puerto.get().strip()
        nombre = self.entrada_nombre.get().strip()

        if not host:
            self.label_estado_login.config(text="⚠ Ingresa la dirección del servidor.")
            return
        if not puerto_str.isdigit():
            self.label_estado_login.config(text="⚠ El puerto debe ser un número.")
            return
        if not nombre:
            self.label_estado_login.config(text="⚠ Ingresa un nombre de usuario.")
            return
        if len(nombre) > 20:
            self.label_estado_login.config(text="⚠ Nombre demasiado largo (máx. 20 caracteres).")
            return

        puerto = int(puerto_str)
        self.label_estado_login.config(text="Conectando...", fg=COLORES["texto_tenue"])
        self.raiz.update()

        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.settimeout(5)
            self.socket_cliente.connect((host, puerto))
            self.socket_cliente.settimeout(None)
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            self.label_estado_login.config(
                text=f"❌ No se pudo conectar: {e}", fg=COLORES["boton"])
            self.socket_cliente = None
            return

        # Enviar registro
        self.nombre_usuario = nombre
        self._enviar_json({"tipo": "registro", "nombre": nombre})

        # Esperar respuesta del servidor
        self.socket_cliente.settimeout(5)
        try:
            buffer = ""
            while True:
                datos = self.socket_cliente.recv(BUFFER_SIZE)
                if not datos:
                    raise ConnectionError("Servidor cerró la conexión.")
                buffer += datos.decode(CODIFICACION)
                if "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    msg = json.loads(linea.strip())
                    if msg["tipo"] == "error":
                        self.label_estado_login.config(
                            text=f"❌ {msg['mensaje']}", fg=COLORES["boton"])
                        self.socket_cliente.close()
                        self.socket_cliente = None
                        return
                    elif msg["tipo"] == "bienvenida":
                        self.conectado = True
                        self.socket_cliente.settimeout(None)
                        # Pasar a pantalla de chat
                        self.frame_login.destroy()
                        self._crear_pantalla_chat()
                        self._mostrar_sistema(msg["mensaje"])
                        if "usuarios" in msg:
                            self._actualizar_lista_usuarios(msg["usuarios"])
                        # Iniciar hilo de recepción
                        self.hilo_recepcion = threading.Thread(
                            target=self._recibir_mensajes, daemon=True)
                        self.hilo_recepcion.start()
                        # Guardar buffer restante
                        self._buffer_pendiente = buffer
                        return
        except (TimeoutError, json.JSONDecodeError, ConnectionError) as e:
            self.label_estado_login.config(
                text=f"❌ Error: {e}", fg=COLORES["boton"])
            try:
                self.socket_cliente.close()
            except OSError:
                pass
            self.socket_cliente = None
            return

    def _enviar_json(self, datos: dict):
        """Envía un diccionario como JSON por el socket."""
        try:
            payload = json.dumps(datos, ensure_ascii=False) + "\n"
            self.socket_cliente.sendall(payload.encode(CODIFICACION))
        except (OSError, AttributeError):
            pass

    def enviar_mensaje(self):
        """Procesa la entrada del usuario y envía el mensaje o comando."""
        if not self.conectado:
            return

        texto = self.entrada_mensaje.get().strip()
        if not texto:
            return

        self.entrada_mensaje.delete(0, tk.END)

        # ── Comandos especiales ──────────────────────────────
        if texto.lower() == "/listar":
            self._enviar_json({"tipo": "comando", "comando": "/listar"})
        elif texto.lower() == "/quitar":
            self._enviar_json({"tipo": "comando", "comando": "/quitar"})
            self.desconectar()
        elif texto.startswith("/"):
            self._mostrar_error(f"Comando desconocido: {texto}")
            self._mostrar_sistema("Comandos disponibles: /listar, /quitar")
        else:
            self._enviar_json({"tipo": "chat", "mensaje": texto})

    def desconectar(self):
        """Se desconecta del servidor y vuelve al login."""
        if self.conectado:
            self.conectado = False
            self._enviar_json({"tipo": "comando", "comando": "/quitar"})
            try:
                self.socket_cliente.close()
            except OSError:
                pass
            self.socket_cliente = None

        # Volver a la pantalla de login
        if hasattr(self, "frame_chat"):
            self.frame_chat.destroy()
        self.mapa_colores_usuario.clear()
        self.indice_color = 0
        self._crear_pantalla_login()

    # ═════════════════════════════════════════════════════════
    # RECEPCIÓN DE MENSAJES (hilo secundario)
    # ═════════════════════════════════════════════════════════

    def _recibir_mensajes(self):
        """Hilo que recibe y procesa mensajes del servidor."""
        buffer = getattr(self, "_buffer_pendiente", "")
        try:
            while self.conectado:
                datos = self.socket_cliente.recv(BUFFER_SIZE)
                if not datos:
                    break

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

                    self._procesar_mensaje(msg)

        except (ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            if self.conectado:
                self.conectado = False
                self.raiz.after(0, lambda: self._mostrar_sistema(
                    "⚠ Se perdió la conexión con el servidor."))
                self.raiz.after(2000, self.desconectar)

    def _procesar_mensaje(self, msg: dict):
        """Procesa un mensaje recibido del servidor (desde hilo)."""
        tipo = msg.get("tipo", "")

        if tipo == "chat":
            remitente = msg.get("remitente", "???")
            contenido = msg.get("mensaje", "")
            hora = msg.get("hora", "")
            es_propio = msg.get("propio", False)
            self.raiz.after(0, lambda: self._mostrar_chat(
                remitente, contenido, hora, es_propio))

        elif tipo == "sistema":
            self.raiz.after(0, lambda: self._mostrar_sistema(msg.get("mensaje", "")))
            if "usuarios" in msg:
                self.raiz.after(0, lambda: self._actualizar_lista_usuarios(
                    msg["usuarios"]))

        elif tipo == "lista":
            self.raiz.after(0, lambda: self._mostrar_lista(msg))
            if "usuarios" in msg:
                self.raiz.after(0, lambda: self._actualizar_lista_usuarios(
                    msg["usuarios"]))

        elif tipo == "error":
            self.raiz.after(0, lambda: self._mostrar_error(msg.get("mensaje", "")))

    # ═════════════════════════════════════════════════════════
    # MOSTRAR MENSAJES EN LA INTERFAZ
    # ═════════════════════════════════════════════════════════

    def _color_usuario(self, nombre: str) -> str:
        """Asigna un color consistente a cada usuario."""
        if nombre not in self.mapa_colores_usuario:
            color = COLORES_USUARIOS[self.indice_color % len(COLORES_USUARIOS)]
            self.mapa_colores_usuario[nombre] = color
            self.indice_color += 1
        return self.mapa_colores_usuario[nombre]

    def _insertar_texto(self, texto: str, tag: str = None):
        """Inserta texto en el área de mensajes."""
        self.area_mensajes.config(state="normal")
        if tag:
            self.area_mensajes.insert(tk.END, texto, tag)
        else:
            self.area_mensajes.insert(tk.END, texto)
        self.area_mensajes.config(state="disabled")
        self.area_mensajes.see(tk.END)

    def _mostrar_chat(self, remitente: str, contenido: str, hora: str,
                       es_propio: bool):
        """Muestra un mensaje de chat en la interfaz."""
        color = self._color_usuario(remitente)

        # Crear tag dinámico para el nombre de este usuario
        tag_nombre = f"user_{remitente}"
        self.area_mensajes.tag_configure(
            tag_nombre, foreground=color, font=("Consolas", 11, "bold"))

        self.area_mensajes.config(state="normal")

        # Hora
        if hora:
            self.area_mensajes.insert(tk.END, f"[{hora}] ", "hora")

        # Indicador de propio
        if es_propio:
            self.area_mensajes.insert(tk.END, f"{remitente} (tú)", "propio_nombre")
        else:
            self.area_mensajes.insert(tk.END, remitente, tag_nombre)

        self.area_mensajes.insert(tk.END, f": {contenido}\n")

        self.area_mensajes.config(state="disabled")
        self.area_mensajes.see(tk.END)

    def _mostrar_sistema(self, mensaje: str):
        """Muestra un mensaje del sistema."""
        self._insertar_texto(f"  ➤ {mensaje}\n", "sistema")

    def _mostrar_error(self, mensaje: str):
        """Muestra un mensaje de error."""
        self._insertar_texto(f"  ✖ {mensaje}\n", "error")

    def _mostrar_lista(self, msg: dict):
        """Muestra la lista de usuarios formateada."""
        titulo = msg.get("mensaje", "Usuarios conectados:")
        usuarios = msg.get("usuarios", [])
        self._insertar_texto(f"\n  ╔══ {titulo} ══╗\n", "lista_titulo")
        for u in usuarios:
            indicador = " ◄ tú" if u == self.nombre_usuario else ""
            self._insertar_texto(f"  ║  ● {u}{indicador}\n", "lista_item")
        self._insertar_texto(f"  ╚{'═' * (len(titulo) + 6)}╝\n\n", "lista_titulo")

    def _actualizar_lista_usuarios(self, usuarios: list):
        """Actualiza el panel lateral de usuarios."""
        self.usuarios_conectados = usuarios
        self.lista_usuarios.delete(0, tk.END)
        for u in sorted(usuarios):
            indicador = " (tú)" if u == self.nombre_usuario else ""
            self.lista_usuarios.insert(tk.END, f"  ● {u}{indicador}")
        self.label_conteo.config(text=f"{len(usuarios)} conectado(s)")

    # ═════════════════════════════════════════════════════════
    # CIERRE
    # ═════════════════════════════════════════════════════════

    def al_cerrar(self):
        """Maneja el cierre de la ventana."""
        if self.conectado:
            self.conectado = False
            self._enviar_json({"tipo": "comando", "comando": "/quitar"})
            try:
                self.socket_cliente.close()
            except OSError:
                pass
        self.raiz.destroy()
        sys.exit(0)

    def ejecutar(self):
        """Inicia el bucle principal de la interfaz."""
        self.raiz.mainloop()


# ─── Punto de entrada ────────────────────────────────────────
if __name__ == "__main__":
    app = ClienteChat()
    app.ejecutar()
