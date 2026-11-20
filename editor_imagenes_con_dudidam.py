import os
import io
import smtplib
import socket
import threading
import tkinter as tk

from tkinter import ttk, filedialog, messagebox
from email.message import EmailMessage

from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageFilter

try:
    from playsound3 import playsound
except ImportError:
    playsound = None


TITULO = "Editor de imágenes - Python"

FORMATOS = [
    ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff"),
    ("Todos los archivos", "*.*")
]


class EditorImagenes:

    def __init__(self, ventana, configuracion_gmail):
        self.ventana = ventana
        self.ventana.title(TITULO)
        self.ventana.geometry("1350x750")
        self.ventana.minsize(950, 600)

        self.imagen_original = None
        self.imagen_actual = None
        self.foto_original = None
        self.foto_actual = None
        self.ruta_imagen = None

        self.inicio_recorte = None
        self.rectangulo_recorte = None
        self.boton_envio = None
        self.gmail_salida = configuracion_gmail["salida"]
        self.gmail_clave = configuracion_gmail["clave"]
        self.destinatario_inicial = configuracion_gmail["destinatario"]
        self.reproductor_editor = None
        self.musica_editor_activa = True
        self.ruta_musica_editor = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "dudidam.mp3"
        )

        self.crear_interfaz()
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar_editor)
        # Al abrir el editor comienza dudidam.mp3 en bucle.
        self.iniciar_musica_editor()

    def iniciar_musica_editor(self):
        """Inicia dudidam.mp3 y lo repite mientras el editor esté abierto."""
        if playsound is None:
            print("Para reproducir música instala playsound3: pip install playsound3")
            return
        if not os.path.isfile(self.ruta_musica_editor):
            print(f"No se encontró la música del editor: {self.ruta_musica_editor}")
            return
        self.reproducir_siguiente_musica_editor()

    def reproducir_siguiente_musica_editor(self):
        if not self.musica_editor_activa:
            return
        try:
            if (self.reproductor_editor is None or
                    not self.reproductor_editor.is_alive()):
                self.reproductor_editor = playsound(
                    self.ruta_musica_editor,
                    block=False
                )
            self.ventana.after(400, self.reproducir_siguiente_musica_editor)
        except Exception as error:
            self.musica_editor_activa = False
            print(f"No se pudo reproducir la música del editor: {error}")

    def detener_musica_editor(self):
        self.musica_editor_activa = False
        if self.reproductor_editor is not None:
            try:
                self.reproductor_editor.stop()
            except Exception as error:
                print(f"No se pudo detener la música del editor: {error}")
            self.reproductor_editor = None

    def cerrar_editor(self):
        self.detener_musica_editor()
        self.ventana.destroy()

    # --------------------------------------------------
    # INTERFAZ
    # --------------------------------------------------

    def crear_interfaz(self):
        encabezado = ttk.Frame(self.ventana, padding=10)
        encabezado.pack(fill="x")

        ttk.Label(
            encabezado,
            text="EDITOR DE IMÁGENES",
            font=("Arial", 19, "bold")
        ).pack(side="left")

        ttk.Button(
            encabezado,
            text="Abrir imagen",
            command=self.abrir_imagen
        ).pack(side="right", padx=5)

        ttk.Button(
            encabezado,
            text="Guardar como",
            command=self.guardar_imagen
        ).pack(side="right", padx=5)

        contenido = ttk.Frame(self.ventana)
        contenido.pack(fill="both", expand=True, padx=8, pady=5)

        # Panel de herramientas desplazable
        contenedor = ttk.Frame(contenido, width=310)
        contenedor.pack(side="left", fill="y", padx=(0, 12))
        contenedor.pack_propagate(False)

        self.canvas_herramientas = tk.Canvas(
            contenedor,
            width=290,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            contenedor,
            orient="vertical",
            command=self.canvas_herramientas.yview
        )

        self.panel = ttk.Frame(self.canvas_herramientas, padding=5)

        self.panel.bind(
            "<Configure>",
            lambda evento: self.canvas_herramientas.configure(
                scrollregion=self.canvas_herramientas.bbox("all")
            )
        )

        self.canvas_herramientas.create_window(
            (0, 0),
            window=self.panel,
            anchor="nw",
            width=290
        )

        self.canvas_herramientas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas_herramientas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas_herramientas.bind(
            "<Enter>",
            lambda evento: self.canvas_herramientas.bind_all(
                "<MouseWheel>", self.desplazar_herramientas
            )
        )
        self.canvas_herramientas.bind(
            "<Leave>",
            lambda evento: self.canvas_herramientas.unbind_all(
                "<MouseWheel>"
            )
        )

        self.crear_herramientas()

        # Panel de imágenes
        vistas = ttk.Frame(contenido)
        vistas.pack(side="left", fill="both", expand=True)
        vistas.columnconfigure(0, weight=1)
        vistas.columnconfigure(1, weight=1)
        vistas.rowconfigure(0, weight=1)

        original_frame = ttk.LabelFrame(
            vistas,
            text="ANTES - Imagen original",
            padding=5
        )
        editada_frame = ttk.LabelFrame(
            vistas,
            text="DESPUÉS - Imagen editada",
            padding=5
        )

        original_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        editada_frame.grid(row=0, column=1, sticky="nsew", padx=5)

        self.canvas_original = tk.Canvas(
            original_frame,
            bg="#222222",
            highlightthickness=0
        )
        self.canvas_actual = tk.Canvas(
            editada_frame,
            bg="#222222",
            highlightthickness=0
        )

        self.canvas_original.pack(fill="both", expand=True)
        self.canvas_actual.pack(fill="both", expand=True)

        ttk.Label(
            original_frame,
            text="IMAGEN ORIGINAL"
        ).pack(pady=5)

        ttk.Label(
            editada_frame,
            text="IMAGEN EDITADA"
        ).pack(pady=5)

        self.canvas_actual.bind("<Button-1>", self.iniciar_recorte)
        self.canvas_actual.bind("<B1-Motion>", self.mover_recorte)
        self.canvas_actual.bind("<ButtonRelease-1>", self.terminar_recorte)

        # Actualizar las vistas al cambiar el tamaño de la ventana
        self.canvas_original.bind(
            "<Configure>",
            lambda evento: self.actualizar_vistas()
            if self.imagen_original is not None else None
        )
        self.canvas_actual.bind(
            "<Configure>",
            lambda evento: self.actualizar_vistas()
            if self.imagen_actual is not None else None
        )

    def desplazar_herramientas(self, evento):
        self.canvas_herramientas.yview_scroll(
            int(-1 * (evento.delta / 120)),
            "units"
        )

    # --------------------------------------------------
    # HERRAMIENTAS Y BOTONES
    # --------------------------------------------------

    def reproducir_sonido_boton(self):
        """Reproduce mambo.mp3 en segundo plano para no congelar Tkinter."""
        if playsound is None:
            print("Para reproducir el sonido instala playsound3: pip install playsound3")
            return

        ruta_sonido = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mambo.mp3")
        if not os.path.isfile(ruta_sonido):
            print(f"No se encontró el sonido: {ruta_sonido}")
            return

        def reproducir():
            try:
                playsound(ruta_sonido)
            except Exception as error:
                print(f"No se pudo reproducir el sonido: {error}")

        threading.Thread(target=reproducir, daemon=True).start()

    def crear_boton(self, padre, texto, funcion):
        # Solo suenan los botones que realizan acciones sobre la imagen.
        # Abrir, guardar y enviar por Gmail quedan sin sonido.
        botones_de_edicion = {
            "Voltear horizontal",
            "Voltear vertical",
            "Izquierda 90°",
            "Derecha 90°",
            "Izquierda 180°",
            "Derecha 180°",
            "Escala de grises",
            "Desenfoque",
            "Nitidez",
            "Sepia",
            "Aplicar ajustes",
            "Cancelar selección",
            "RESTABLECER IMAGEN",
        }

        def ejecutar():
            if texto in botones_de_edicion:
                self.reproducir_sonido_boton()
            funcion()

        return ttk.Button(
            padre,
            text=texto,
            command=ejecutar
        )

    def agregar_boton(self, padre, texto, funcion):
        boton = self.crear_boton(padre, texto, funcion)
        boton.pack(fill="x", pady=3)
        return boton

    def crear_herramientas(self):

        # GMAIL: sección visible al principio del panel
        gmail = ttk.LabelFrame(
            self.panel,
            text="ENVIAR IMAGEN POR GMAIL",
            padding=8
        )
        gmail.pack(fill="x", pady=(0, 10))

        ttk.Label(
            gmail,
            text="Correo del destinatario:"
        ).pack(anchor="w")

        self.correo_destino = tk.StringVar(value=self.destinatario_inicial)

        ttk.Entry(
            gmail,
            textvariable=self.correo_destino
        ).pack(fill="x", pady=5)

        self.boton_envio = self.agregar_boton(
            gmail,
            "ENVIAR FOTO EDITADA POR GMAIL",
            self.enviar_gmail
        )

        # ARCHIVO
        archivo = ttk.LabelFrame(self.panel, text="ARCHIVO", padding=8)
        archivo.pack(fill="x", pady=5)

        self.agregar_boton(archivo, "Abrir imagen", self.abrir_imagen)
        self.agregar_boton(archivo, "Guardar como", self.guardar_imagen)

        # VOLTEAR
        voltear = ttk.LabelFrame(self.panel, text="VOLTEAR", padding=8)
        voltear.pack(fill="x", pady=5)

        self.agregar_boton(
            voltear,
            "Voltear horizontal",
            lambda: self.aplicar(Image.Transpose.FLIP_LEFT_RIGHT)
        )
        self.agregar_boton(
            voltear,
            "Voltear vertical",
            lambda: self.aplicar(Image.Transpose.FLIP_TOP_BOTTOM)
        )

        # ROTAR
        rotar = ttk.LabelFrame(self.panel, text="ROTAR", padding=8)
        rotar.pack(fill="x", pady=5)

        self.agregar_boton(rotar, "Izquierda 90°", lambda: self.rotar(90))
        self.agregar_boton(rotar, "Derecha 90°", lambda: self.rotar(-90))
        self.agregar_boton(rotar, "Izquierda 180°", lambda: self.rotar(180))
        self.agregar_boton(rotar, "Derecha 180°", lambda: self.rotar(180))

        # CONVERSIÓN
        conversion = ttk.LabelFrame(
            self.panel, text="CONVERSIÓN", padding=8
        )
        conversion.pack(fill="x", pady=5)
        self.agregar_boton(conversion, "Escala de grises", self.grises)

        # FILTROS
        filtros = ttk.LabelFrame(self.panel, text="FILTROS", padding=8)
        filtros.pack(fill="x", pady=5)

        self.agregar_boton(filtros, "Desenfoque", self.desenfoque)
        self.agregar_boton(filtros, "Nitidez", self.nitidez)
        self.agregar_boton(filtros, "Sepia", self.sepia)

        # AJUSTES
        ajustes = ttk.LabelFrame(self.panel, text="AJUSTES", padding=8)
        ajustes.pack(fill="x", pady=5)

        self.brillo = tk.DoubleVar(value=1.0)
        self.contraste = tk.DoubleVar(value=1.0)
        self.saturacion = tk.DoubleVar(value=1.0)

        self.crear_control(ajustes, "Brillo", self.brillo)
        self.crear_control(ajustes, "Contraste", self.contraste)
        self.crear_control(ajustes, "Saturación", self.saturacion)

        self.agregar_boton(
            ajustes, "Aplicar ajustes", self.aplicar_ajustes
        )

        # RECORTE
        recorte = ttk.LabelFrame(self.panel, text="RECORTE", padding=8)
        recorte.pack(fill="x", pady=5)

        ttk.Label(
            recorte,
            text="Arrastra el ratón sobre la imagen editada."
        ).pack(anchor="w")

        self.agregar_boton(
            recorte, "Cancelar selección", self.cancelar_recorte
        )

        # RESTABLECER
        restaurar = ttk.LabelFrame(
            self.panel, text="RESTABLECER", padding=8
        )
        restaurar.pack(fill="x", pady=5)

        self.agregar_boton(
            restaurar,
            "RESTABLECER IMAGEN",
            self.restablecer_imagen
        )

    def crear_control(self, padre, nombre, variable):
        ttk.Label(padre, text=nombre).pack(anchor="w")
        ttk.Scale(
            padre,
            from_=0.2,
            to=2.0,
            variable=variable,
            orient="horizontal"
        ).pack(fill="x", pady=3)

    # --------------------------------------------------
    # ABRIR Y MOSTRAR IMÁGENES
    # --------------------------------------------------

    def abrir_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=FORMATOS
        )

        if not ruta:
            return

        try:
            imagen = Image.open(ruta).convert("RGB")
            self.imagen_original = imagen.copy()
            self.imagen_actual = imagen.copy()
            self.ruta_imagen = ruta

            self.restablecer_controles()
            self.cancelar_recorte()
            self.actualizar_vistas()

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la imagen:\n{error}"
            )

    def actualizar_vistas(self):
        if self.imagen_original is None or self.imagen_actual is None:
            return

        self.mostrar_preview(
            self.canvas_original,
            self.imagen_original,
            "original"
        )
        self.mostrar_preview(
            self.canvas_actual,
            self.imagen_actual,
            "actual"
        )

    def mostrar_preview(self, canvas, imagen, tipo):
        canvas.update_idletasks()

        ancho = max(canvas.winfo_width(), 100)
        alto = max(canvas.winfo_height(), 100)

        copia = imagen.copy()
        copia.thumbnail(
            (max(ancho - 10, 1), max(alto - 10, 1)),
            Image.Resampling.LANCZOS
        )

        foto = ImageTk.PhotoImage(copia)
        canvas.delete("all")
        canvas.create_image(
            ancho // 2,
            alto // 2,
            image=foto,
            anchor="center"
        )

        if tipo == "original":
            self.foto_original = foto
        else:
            self.foto_actual = foto

    # --------------------------------------------------
    # OPERACIONES DE IMAGEN
    # --------------------------------------------------

    def comprobar_imagen(self):
        if self.imagen_actual is None:
            messagebox.showwarning(
                "Aviso",
                "Primero debes abrir una imagen."
            )
            return False
        return True

    def aplicar(self, operacion):
        if not self.comprobar_imagen():
            return

        try:
            self.imagen_actual = self.imagen_actual.transpose(operacion)
            self.actualizar_vistas()
        except Exception as error:
            messagebox.showerror("Error", str(error))

    def rotar(self, grados):
        if not self.comprobar_imagen():
            return

        self.imagen_actual = self.imagen_actual.rotate(
            grados,
            expand=True
        )
        self.actualizar_vistas()

    def grises(self):
        if not self.comprobar_imagen():
            return

        self.imagen_actual = ImageOps.grayscale(
            self.imagen_actual
        ).convert("RGB")
        self.actualizar_vistas()

    def desenfoque(self):
        if not self.comprobar_imagen():
            return

        self.imagen_actual = self.imagen_actual.filter(
            ImageFilter.GaussianBlur(radius=3)
        )
        self.actualizar_vistas()

    def nitidez(self):
        if not self.comprobar_imagen():
            return

        self.imagen_actual = self.imagen_actual.filter(
            ImageFilter.UnsharpMask(
                radius=2,
                percent=150,
                threshold=3
            )
        )
        self.actualizar_vistas()

    def sepia(self):
        if not self.comprobar_imagen():
            return

        gris = ImageOps.grayscale(self.imagen_actual)
        sepia = ImageOps.colorize(
            gris,
            "#704214",
            "#FFDDA0"
        )
        self.imagen_actual = sepia.convert("RGB")
        self.actualizar_vistas()

    def aplicar_ajustes(self):
        if not self.comprobar_imagen():
            return

        try:
            imagen = ImageEnhance.Brightness(
                self.imagen_actual
            ).enhance(self.brillo.get())

            imagen = ImageEnhance.Contrast(
                imagen
            ).enhance(self.contraste.get())

            imagen = ImageEnhance.Color(
                imagen
            ).enhance(self.saturacion.get())

            self.imagen_actual = imagen
            self.actualizar_vistas()

        except Exception as error:
            messagebox.showerror("Error", str(error))

    # --------------------------------------------------
    # RESTABLECER IMAGEN Y CONTROLES
    # --------------------------------------------------

    def restablecer_controles(self):
        """Devuelve los controles de ajuste a sus valores iniciales."""
        self.brillo.set(1.0)
        self.contraste.set(1.0)
        self.saturacion.set(1.0)

    def restablecer_imagen(self):
        """
        Recupera la imagen original en el panel derecho.
        No borra ni oculta ninguna de las dos vistas.
        """
        if self.imagen_original is None:
            messagebox.showwarning(
                "Aviso",
                "Primero debes abrir una imagen."
            )
            return

        self.imagen_actual = self.imagen_original.copy()
        self.restablecer_controles()
        self.cancelar_recorte()
        self.actualizar_vistas()

        messagebox.showinfo(
            "Imagen restablecida",
            "La imagen editada volvió a su estado original."
        )

    # Mantener el nombre anterior por compatibilidad
    def restaurar(self):
        self.restablecer_imagen()

    # --------------------------------------------------
    # RECORTE CON EL RATÓN
    # --------------------------------------------------

    def iniciar_recorte(self, evento):
        if not self.comprobar_imagen():
            return

        self.cancelar_recorte()
        self.inicio_recorte = (evento.x, evento.y)

        self.rectangulo_recorte = self.canvas_actual.create_rectangle(
            evento.x,
            evento.y,
            evento.x,
            evento.y,
            outline="red",
            width=2
        )

    def mover_recorte(self, evento):
        if self.inicio_recorte is None:
            return

        x1, y1 = self.inicio_recorte
        self.canvas_actual.coords(
            self.rectangulo_recorte,
            x1, y1, evento.x, evento.y
        )

    def terminar_recorte(self, evento):
        if self.inicio_recorte is None:
            return

        canvas = self.canvas_actual
        x1, y1 = self.inicio_recorte
        x2, y2 = evento.x, evento.y

        ancho_canvas = canvas.winfo_width()
        alto_canvas = canvas.winfo_height()

        ancho_imagen, alto_imagen = self.imagen_actual.size

        escala = min(
            (ancho_canvas - 10) / ancho_imagen,
            (alto_canvas - 10) / alto_imagen
        )

        ancho_mostrado = ancho_imagen * escala
        alto_mostrado = alto_imagen * escala

        offset_x = (ancho_canvas - ancho_mostrado) / 2
        offset_y = (alto_canvas - alto_mostrado) / 2

        izquierda = max(0, min(x1, x2) - offset_x)
        arriba = max(0, min(y1, y2) - offset_y)
        derecha = min(ancho_mostrado, max(x1, x2) - offset_x)
        abajo = min(alto_mostrado, max(y1, y2) - offset_y)

        izquierda = int(izquierda / escala)
        arriba = int(arriba / escala)
        derecha = int(derecha / escala)
        abajo = int(abajo / escala)

        if derecha > izquierda and abajo > arriba:
            self.imagen_actual = self.imagen_actual.crop(
                (izquierda, arriba, derecha, abajo)
            )
            self.actualizar_vistas()

        self.cancelar_recorte()

    def cancelar_recorte(self):
        if self.rectangulo_recorte is not None:
            self.canvas_actual.delete(self.rectangulo_recorte)

        self.rectangulo_recorte = None
        self.inicio_recorte = None

    # --------------------------------------------------
    # GUARDAR IMAGEN
    # --------------------------------------------------

    def guardar_imagen(self):
        if not self.comprobar_imagen():
            return

        ruta = filedialog.asksaveasfilename(
            title="Guardar imagen",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPG", "*.jpg"),
                ("BMP", "*.bmp"),
                ("WEBP", "*.webp")
            ]
        )

        if not ruta:
            return

        try:
            imagen = self.imagen_actual.copy()

            if ruta.lower().endswith((".jpg", ".jpeg")):
                imagen.convert("RGB").save(ruta, quality=95)
            else:
                imagen.save(ruta)

            messagebox.showinfo(
                "Guardado",
                "La imagen se guardó correctamente."
            )

        except Exception as error:
            messagebox.showerror(
                "Error al guardar",
                str(error)
            )

    # --------------------------------------------------
    # ENVIAR IMAGEN EDITADA POR GMAIL
    # --------------------------------------------------

    def enviar_gmail(self):
        if not self.comprobar_imagen():
            return

        destinatario = self.correo_destino.get().strip()

        if not destinatario or "@" not in destinatario:
            messagebox.showwarning(
                "Correo incorrecto",
                "Escribe un correo válido del destinatario."
            )
            return

        usuario = self.gmail_salida
        clave = self.gmail_clave

        if not usuario or not clave:
            messagebox.showerror(
                "Faltan credenciales",
                "Cierra el editor y vuelve a abrirlo para ingresar "
                "los datos de Gmail."
            )
            return

        memoria = io.BytesIO()
        self.imagen_actual.save(memoria, format="PNG")
        datos_imagen = memoria.getvalue()

        self.boton_envio.config(
            state="disabled",
            text="Enviando..."
        )

        hilo = threading.Thread(
            target=self.procesar_envio_gmail,
            args=(usuario, clave, destinatario, datos_imagen),
            daemon=True
        )
        hilo.start()

    def procesar_envio_gmail(
        self,
        usuario,
        clave,
        destinatario,
        datos_imagen
    ):
        try:
            mensaje = EmailMessage()
            mensaje["Subject"] = "Imagen editada"
            mensaje["From"] = usuario
            mensaje["To"] = destinatario

            mensaje.set_content(
                "Hola.\n\n"
                "Te envío la imagen editada desde mi editor "
                "de imágenes en Python."
            )

            mensaje.add_attachment(
                datos_imagen,
                maintype="image",
                subtype="png",
                filename="imagen_editada.png"
            )

            with smtplib.SMTP(
                "smtp.gmail.com",
                587,
                timeout=30
            ) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(usuario, clave)
                servidor.send_message(mensaje)

            self.ventana.after(
                0,
                lambda: self.resultado_envio(
                    True,
                    "¡La imagen se envió correctamente por Gmail!"
                )
            )

        except socket.gaierror:
            mensaje_error = (
                "Windows no pudo encontrar el servidor de Gmail "
                "(smtp.gmail.com).\n\n"
                "Qué hacer:\n"
                "1. Comprueba que tienes Internet abriendo una página web.\n"
                "2. Si Internet funciona, reinicia el router o prueba otra red.\n"
                "3. Si estás en una red escolar o pública, puede bloquear "
                "el envío SMTP. Prueba desde otra red.\n\n"
                "No cambies tu contraseña: este error normalmente no "
                "se debe a la contraseña."
            )
            self.ventana.after(
                0,
                lambda: self.resultado_envio(False, mensaje_error)
            )
        except (TimeoutError, socket.timeout):
            mensaje_error = (
                "La conexión con Gmail tardó demasiado. Comprueba Internet "
                "y vuelve a intentarlo."
            )
            self.ventana.after(
                0,
                lambda: self.resultado_envio(False, mensaje_error)
            )
        except smtplib.SMTPAuthenticationError:
            mensaje_error = (
                "Google rechazó el inicio de sesión. Comprueba que el correo "
                "de salida sea tu cuenta y que hayas copiado correctamente "
                "la contraseña de aplicación de Google (no la contraseña "
                "normal de Gmail)."
            )
            self.ventana.after(
                0,
                lambda: self.resultado_envio(False, mensaje_error)
            )
        except Exception as error:
            mensaje_error = f"{type(error).__name__}: {error}"
            self.ventana.after(
                0,
                lambda: self.resultado_envio(
                    False,
                    f"No se pudo enviar el correo:\n{mensaje_error}"
                )
            )

    def resultado_envio(self, correcto, mensaje):
        self.boton_envio.config(
            state="normal",
            text="ENVIAR FOTO EDITADA POR GMAIL"
        )

        if correcto:
            messagebox.showinfo("Gmail", mensaje)
        else:
            messagebox.showerror("Error de Gmail", mensaje)


class VentanaConfiguracionGmail:
    """Solicita los datos de Gmail al iniciar el programa."""

    def __init__(self, ventana):
        self.ventana = ventana
        self.resultado = None
        self.reproductor_musica = None
        self.musica_activa = True
        self.ruta_musica = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "hachimi-chimici-mambo.mp3"
        )

        self.ventana.title("Configuración de Gmail")
        self.ventana.geometry("440x330")
        self.ventana.resizable(False, False)

        marco = ttk.Frame(ventana, padding=20)
        marco.pack(fill="both", expand=True)

        ttk.Label(
            marco,
            text="CONFIGURAR CORREO",
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 8))

        ttk.Label(
            marco,
            text="Ingresa los datos que se usarán para enviar las imágenes."
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(marco, text="Gmail de salida (tu cuenta):").pack(anchor="w")
        self.salida = tk.StringVar()
        ttk.Entry(
            marco,
            textvariable=self.salida
        ).pack(fill="x", pady=(3, 10))

        ttk.Label(marco, text="Correo del destinatario:").pack(anchor="w")
        self.destinatario = tk.StringVar()
        ttk.Entry(
            marco,
            textvariable=self.destinatario
        ).pack(fill="x", pady=(3, 10))

        ttk.Label(marco, text="Contraseña de aplicación de Google:").pack(anchor="w")
        self.clave = tk.StringVar()
        ttk.Entry(
            marco,
            textvariable=self.clave,
            show="*"
        ).pack(fill="x", pady=(3, 5))

        ttk.Label(
            marco,
            text="La contraseña se usa solo durante esta sesión y no se guarda.",
            wraplength=390
        ).pack(anchor="w", pady=(0, 10))

        botones = ttk.Frame(marco)
        botones.pack(fill="x")

        ttk.Button(
            botones,
            text="Salir",
            command=self.cancelar
        ).pack(side="right", padx=(5, 0))

        ttk.Button(
            botones,
            text="Continuar",
            command=self.aceptar
        ).pack(side="right")

        self.ventana.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.ventana.bind("<Return>", lambda evento: self.aceptar())
        self.ventana.bind("<Escape>", lambda evento: self.cancelar())

        # La música se reproduce en bucle solo mientras esta ventana está abierta.
        self.iniciar_musica()

    def iniciar_musica(self):
        if playsound is None:
            print("Para reproducir la música instala playsound3: pip install playsound3")
            return
        if not os.path.isfile(self.ruta_musica):
            print(f"No se encontró el archivo de música: {self.ruta_musica}")
            return
        self.reproducir_siguiente_fragmento()

    def reproducir_siguiente_fragmento(self):
        if not self.musica_activa:
            return
        try:
            if self.reproductor_musica is None or not self.reproductor_musica.is_alive():
                self.reproductor_musica = playsound(self.ruta_musica, block=False)
            self.ventana.after(400, self.reproducir_siguiente_fragmento)
        except Exception as error:
            self.musica_activa = False
            print(f"No se pudo reproducir la música: {error}")

    def detener_musica(self):
        self.musica_activa = False
        if self.reproductor_musica is not None:
            try:
                self.reproductor_musica.stop()
            except Exception as error:
                print(f"No se pudo detener la música: {error}")
            self.reproductor_musica = None

    def aceptar(self):
        salida = self.salida.get().strip()
        destinatario = self.destinatario.get().strip()
        clave = self.clave.get().strip()

        if not salida or "@" not in salida:
            messagebox.showwarning(
                "Correo de salida",
                "Escribe una dirección Gmail válida.",
                parent=self.ventana
            )
            return

        if not destinatario or "@" not in destinatario:
            messagebox.showwarning(
                "Destinatario",
                "Escribe una dirección de correo válida.",
                parent=self.ventana
            )
            return

        if not clave:
            messagebox.showwarning(
                "Contraseña de aplicación",
                "Ingresa la contraseña de aplicación de Google.",
                parent=self.ventana
            )
            return

        self.resultado = {
            "salida": salida,
            "destinatario": destinatario,
            "clave": clave
        }
        self.detener_musica()
        self.ventana.destroy()

    def cancelar(self):
        self.resultado = None
        self.detener_musica()
        self.ventana.destroy()


def main():
    # Primero se solicitan los datos de Gmail.
    ventana_config = tk.Tk()
    dialogo = VentanaConfiguracionGmail(ventana_config)
    ventana_config.mainloop()

    if dialogo.resultado is None:
        return

    # Después se abre el editor con los datos introducidos.
    ventana_editor = tk.Tk()
    EditorImagenes(ventana_editor, dialogo.resultado)
    ventana_editor.mainloop()


if __name__ == "__main__":
    main()
