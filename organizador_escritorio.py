import sys
import os
import shutil
import json
import winreg
from pathlib import Path
from collections import Counter
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QMessageBox, QFrame,
                             QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
                             QMenu, QColorDialog, QGroupBox, QGridLayout, QScrollBar,
                             QTabWidget, QSpinBox, QDoubleSpinBox, QSlider, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QPoint, QMimeData, pyqtSignal, QSettings, QFileInfo, QSize, QTimer, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QFont, QImage, QIcon, QWheelEvent, QPixmap, QDrag
from PyQt5.QtWidgets import QFileIconProvider


class CasillaVentana(QWidget):
    """Ventana independiente que representa una casilla organizadora"""
    archivo_soltado = pyqtSignal(str, str)  # emite: ruta_archivo, nombre_casilla
    casilla_eliminada = pyqtSignal(object)  # emite: referencia a la casilla
    
    def __init__(self, nombre, carpeta_path, posicion=None, parent_app=None):
        super().__init__()
        self.nombre = nombre
        # Asegurar que carpeta_path sea un objeto Path
        self.carpeta_path = Path(carpeta_path) if not isinstance(carpeta_path, Path) else carpeta_path
        self.parent_app = parent_app
        self.expandida = False
        self.tamano_colapsado = (140, 50)  # Más pequeño y compacto
        self.tamano_expandido = (280, 400)
        # Guardar posiciones originales de casillas movidas cuando se expande
        self.posiciones_originales = {}
        # Tamaños personalizados del usuario (colapsado y expandido)
        self.tamano_personalizado_colapsado = None
        self.tamano_personalizado_expandido = None
        # Tamaño de iconos (por defecto 24x24 píxeles)
        self.tamano_iconos = 24
        # Multiplicador de resolución de iconos (por defecto 2x para mejor calidad)
        self.multiplicador_resolucion_iconos = 2.0
        # Tipo de vista: "lista" o "cuadricula"
        self.tipo_vista = "lista"
        # Velocidad de scroll (porcentaje, 100% = normal, por defecto 100%)
        self.velocidad_scroll = 100.0
        # Label temporal para mostrar porcentaje
        self.label_porcentaje = None
        self.timer_porcentaje = None
        # Estado de redimensionamiento
        self.resizing = False
        self.resize_start_pos = None
        self.resize_start_size = None
        self.resize_start_window_pos = None
        self.resize_corner = None
        self.setup_ui()
        self.setup_drag_drop()
        
        # Restaurar posición si se proporciona (después de que la UI esté lista)
        QApplication.processEvents()
        if posicion:
            pos_ajustada = self.limitar_a_pantalla(QPoint(posicion[0], posicion[1]))
            pos_ajustada = self.evitar_colisiones(pos_ajustada)
            self.move(pos_ajustada)
        else:
            # Posición por defecto (centro de la pantalla con offset)
            screen = QApplication.primaryScreen().geometry()
            pos_default = QPoint(screen.width() // 2 - 100, screen.height() // 2 - 75)
            pos_ajustada = self.limitar_a_pantalla(pos_default)
            pos_ajustada = self.evitar_colisiones(pos_ajustada)
            self.move(pos_ajustada)
        
        # Aplicar tamaño personalizado colapsado si existe
        if self.tamano_personalizado_colapsado:
            QApplication.processEvents()
            self.resize(self.tamano_personalizado_colapsado[0], self.tamano_personalizado_colapsado[1])
        
        # Actualizar lista después de que la ventana esté lista
        self.actualizar_lista_archivos()
        
    def setup_ui(self):
        """Configura la interfaz de la casilla"""
        # Hacer la ventana transparente y sin bordes
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Tamaño inicial de la casilla (colapsada) - permitir redimensionamiento
        ancho_inicial = self.tamano_colapsado[0]
        alto_inicial = self.tamano_colapsado[1]
        if self.tamano_personalizado_colapsado:
            ancho_inicial, alto_inicial = self.tamano_personalizado_colapsado
        
        # Asegurar que el tamaño sea válido
        ancho_inicial = max(100, min(800, ancho_inicial))
        alto_inicial = max(40, min(600, alto_inicial))
        
        self.setMinimumSize(100, 40)  # Más pequeño para casillas compactas
        self.setMaximumSize(800, 600)
        self.resize(ancho_inicial, alto_inicial)
        self.setVisible(True)  # Asegurar que sea visible
        
        # Frame principal
        self.frame = QFrame()
        self.frame.setFrameStyle(QFrame.Box)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 150, 200, 140);
                border: 2px solid rgba(50, 100, 150, 220);
                border-radius: 12px;
            }
        """)
        
        # Layout del frame
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(6, 4, 6, 4)
        frame_layout.setSpacing(2)
        
        # Barra superior con botón y título
        barra_superior = QHBoxLayout()
        barra_superior.setContentsMargins(0, 0, 0, 0)
        barra_superior.setSpacing(5)
        
        # Botón expandir/colapsar
        self.btn_expandir = QPushButton("▼")
        self.btn_expandir.setFixedSize(18, 18)
        self.btn_expandir.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 110, 150, 200);
                color: white;
                border: none;
                border-radius: 9px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: rgba(90, 130, 170, 220);
            }
        """)
        self.btn_expandir.clicked.connect(self.toggle_expandir)
        
        # Label con el nombre
        self.label_nombre = QLabel(self.nombre)
        self.label_nombre.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_nombre.setWordWrap(False)
        self.label_nombre.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 11px;
                background-color: transparent;
                padding: 0px;
            }
        """)
        self.label_nombre.setTextFormat(Qt.PlainText)
        
        barra_superior.addWidget(self.btn_expandir)
        barra_superior.addWidget(self.label_nombre, stretch=1)
        barra_superior.addStretch()
        
        # Contador de archivos (con margen izquierdo para alinearse con el título)
        self.contador_layout = QHBoxLayout()
        self.contador_layout.setContentsMargins(28, 0, 0, 0)
        self.contador_layout.setSpacing(0)
        
        self.label_contador = QLabel("0 archivos")
        self.label_contador.setAlignment(Qt.AlignLeft)
        self.label_contador.setStyleSheet("""
            QLabel {
                color: rgba(220, 220, 220, 220);
                font-size: 10px;
                background-color: transparent;
                padding: 0px;
            }
        """)
        self.contador_layout.addWidget(self.label_contador)
        self.contador_layout.addStretch()
        
        # Widget contenedor para el contador (para poder ocultarlo completamente)
        self.contador_widget = QWidget()
        self.contador_widget.setLayout(self.contador_layout)
        
        # Lista de archivos (inicialmente oculta)
        self.lista_archivos = QListWidget()
        self.lista_archivos.setMinimumHeight(0)
        self.lista_archivos.setMaximumHeight(0)
        self.lista_archivos.setVisible(False)
        # Habilitar scroll con rueda del mouse
        self.lista_archivos.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lista_archivos.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        # Habilitar barras de scroll cuando sea necesario
        self.lista_archivos.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lista_archivos.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Configurar scrollbar (se actualizará con la velocidad configurada)
        self.actualizar_velocidad_scroll()
        # Asegurar que el widget pueda recibir eventos de scroll
        self.lista_archivos.setFocusPolicy(Qt.WheelFocus)
        self.lista_archivos.setMouseTracking(True)
        # Asegurar que el widget acepte eventos de scroll
        self.lista_archivos.setAttribute(Qt.WA_AcceptTouchEvents, False)
        # Configurar tamaño inicial de iconos
        self.actualizar_tamano_iconos()
        # Configurar tipo de vista inicial
        self.aplicar_tipo_vista()
        self.lista_archivos.setStyleSheet("""
            QListWidget {
                background-color: rgba(60, 100, 140, 120);
                border: 1px solid rgba(80, 120, 160, 180);
                border-radius: 6px;
                color: white;
                font-size: 10px;
                padding: 3px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid rgba(80, 120, 160, 100);
            }
            QListWidget::item:hover {
                background-color: rgba(80, 120, 160, 150);
            }
            QListWidget::item:selected {
                background-color: rgba(100, 140, 180, 200);
            }
            QScrollBar:vertical {
                background-color: rgba(50, 80, 120, 180);
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(100, 140, 180, 220);
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(120, 160, 200, 255);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:vertical:disabled {
                background-color: rgba(50, 80, 120, 100);
            }
            QScrollBar:horizontal {
                background-color: rgba(50, 80, 120, 150);
                height: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(100, 140, 180, 200);
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(120, 160, 200, 240);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        self.lista_archivos.itemDoubleClicked.connect(self.abrir_archivo)
        # Habilitar drag and drop en los items de la lista
        self.lista_archivos.setDragEnabled(True)
        self.lista_archivos.setDragDropMode(QListWidget.DragDrop)
        self.lista_archivos.setDefaultDropAction(Qt.MoveAction)
        # Conectar el evento de inicio de drag para personalizar el MIME data
        self.lista_archivos.startDrag = self.iniciar_drag_archivo
        
        frame_layout.addLayout(barra_superior)
        frame_layout.addWidget(self.contador_widget)
        frame_layout.addWidget(self.lista_archivos, stretch=1)
        
        # Ocultar contador inicialmente (solo se muestra cuando está expandida)
        self.contador_widget.setVisible(False)
        
        self.frame.setLayout(frame_layout)
        
        # Asegurar que el título se trunque si es muy largo
        self.actualizar_titulo()
        
        # Layout principal de la ventana
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        
        self.setLayout(main_layout)
        
        # Permitir mover la ventana
        self.old_pos = None
    
    def actualizar_titulo(self):
        """Actualiza el título truncándolo si es muy largo"""
        nombre = self.nombre
        # Calcular ancho disponible (ancho de la casilla menos botón y márgenes)
        ancho_disponible = self.width() - 40  # 22 botón + 18 márgenes
        if ancho_disponible < 40:
            ancho_disponible = 40
        
        # Estimar caracteres que caben (aproximadamente 7px por carácter)
        max_caracteres = max(10, int(ancho_disponible / 7))
        
        if len(nombre) > max_caracteres:
            texto_truncado = nombre[:max_caracteres-3] + "..."
            self.label_nombre.setText(texto_truncado)
            self.label_nombre.setToolTip(nombre)  # Mostrar nombre completo al pasar el mouse
        else:
            self.label_nombre.setText(nombre)
            self.label_nombre.setToolTip("")
        
    def setup_drag_drop(self):
        """Configura el arrastre y soltado de archivos"""
        self.setAcceptDrops(True)
    
    def aplicar_colores(self, colores):
        """Aplica los colores personalizados a todos los elementos de la casilla"""
        # Obtener colores con valores por defecto
        r_fondo, g_fondo, b_fondo, a_fondo = colores.get("fondo", (100, 150, 200, 140))
        r_borde, g_borde, b_borde, a_borde = colores.get("borde", (50, 100, 150, 220))
        r_boton, g_boton, b_boton, a_boton = colores.get("boton_expandir", (70, 110, 150, 200))
        r_texto, g_texto, b_texto, a_texto = colores.get("texto", (255, 255, 255, 255))
        r_lista_fondo, g_lista_fondo, b_lista_fondo, a_lista_fondo = colores.get("lista_fondo", (60, 100, 140, 120))
        r_lista_borde, g_lista_borde, b_lista_borde, a_lista_borde = colores.get("lista_borde", (80, 120, 160, 180))
        
        # Aplicar color al frame principal
        self.frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({r_fondo}, {g_fondo}, {b_fondo}, {a_fondo});
                border: 2px solid rgba({r_borde}, {g_borde}, {b_borde}, {a_borde});
                border-radius: 12px;
            }}
        """)
        
        # Aplicar color al botón expandir
        r_boton_hover = min(255, r_boton + 20)
        g_boton_hover = min(255, g_boton + 20)
        b_boton_hover = min(255, b_boton + 20)
        a_boton_hover = min(255, a_boton + 20)
        self.btn_expandir.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r_boton}, {g_boton}, {b_boton}, {a_boton});
                color: rgba({r_texto}, {g_texto}, {b_texto}, {a_texto});
                border: none;
                border-radius: 9px;
                font-weight: bold;
                font-size: 9px;
            }}
            QPushButton:hover {{
                background-color: rgba({r_boton_hover}, {g_boton_hover}, {b_boton_hover}, {a_boton_hover});
            }}
        """)
        
        # Aplicar color al texto
        self.label_nombre.setStyleSheet(f"""
            QLabel {{
                color: rgba({r_texto}, {g_texto}, {b_texto}, {a_texto});
                font-weight: bold;
                font-size: 11px;
                background-color: transparent;
                padding: 0px;
            }}
        """)
        
        # Aplicar color al contador (más transparente que el texto principal)
        a_contador = max(180, a_texto - 40)
        self.label_contador.setStyleSheet(f"""
            QLabel {{
                color: rgba({r_texto}, {g_texto}, {b_texto}, {a_contador});
                font-size: 10px;
                background-color: transparent;
                padding: 0px;
            }}
        """)
        
        # Aplicar colores a la lista de archivos
        r_lista_hover = min(255, r_lista_fondo + 20)
        g_lista_hover = min(255, g_lista_fondo + 20)
        b_lista_hover = min(255, b_lista_fondo + 20)
        r_lista_selected = min(255, r_lista_fondo + 40)
        g_lista_selected = min(255, g_lista_fondo + 40)
        b_lista_selected = min(255, b_lista_fondo + 40)
        r_lista_borde_item = min(255, r_lista_borde - 20)
        g_lista_borde_item = min(255, g_lista_borde - 20)
        b_lista_borde_item = min(255, b_lista_borde - 20)
        
        self.lista_archivos.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba({r_lista_fondo}, {g_lista_fondo}, {b_lista_fondo}, {a_lista_fondo});
                border: 1px solid rgba({r_lista_borde}, {g_lista_borde}, {b_lista_borde}, {a_lista_borde});
                border-radius: 6px;
                color: rgba({r_texto}, {g_texto}, {b_texto}, {a_texto});
                font-size: 10px;
                padding: 3px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid rgba({r_lista_borde_item}, {g_lista_borde_item}, {b_lista_borde_item}, 100);
            }}
            QListWidget::item:hover {{
                background-color: rgba({r_lista_hover}, {g_lista_hover}, {b_lista_hover}, 150);
            }}
            QListWidget::item:selected {{
                background-color: rgba({r_lista_selected}, {g_lista_selected}, {b_lista_selected}, 200);
            }}
            QScrollBar:vertical {{
                background-color: rgba({r_lista_fondo}, {g_lista_fondo}, {b_lista_fondo}, 150);
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgba({r_lista_borde}, {g_lista_borde}, {b_lista_borde}, 200);
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgba({r_lista_borde}, {g_lista_borde}, {b_lista_borde}, 240);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: rgba({r_lista_fondo}, {g_lista_fondo}, {b_lista_fondo}, 150);
                height: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: rgba({r_lista_borde}, {g_lista_borde}, {b_lista_borde}, 200);
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: rgba({r_lista_borde}, {g_lista_borde}, {b_lista_borde}, 240);
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        
    def detectar_borde_resize(self, pos):
        """Detecta en qué borde está el mouse para redimensionar"""
        ancho = self.width()
        alto = self.height()
        margen_resize = 10
        
        x, y = pos.x(), pos.y()
        
        # Verificar bordes (evitar área del botón expandir en esquina superior izquierda)
        en_borde_izquierdo = x <= margen_resize and y > 30
        en_borde_derecho = x >= ancho - margen_resize
        en_borde_superior = y <= margen_resize and x > 30
        en_borde_inferior = y >= alto - margen_resize
        
        # Esquinas
        en_esquina_superior_izquierda = (x <= margen_resize and y <= margen_resize and x > 30)
        en_esquina_superior_derecha = (x >= ancho - margen_resize and y <= margen_resize)
        en_esquina_inferior_izquierda = (x <= margen_resize and y >= alto - margen_resize and y > 30)
        en_esquina_inferior_derecha = (x >= ancho - margen_resize and y >= alto - margen_resize)
        
        if en_esquina_inferior_derecha:
            return 'esquina_inferior_derecha'
        elif en_esquina_inferior_izquierda:
            return 'esquina_inferior_izquierda'
        elif en_esquina_superior_derecha:
            return 'esquina_superior_derecha'
        elif en_esquina_superior_izquierda:
            return 'esquina_superior_izquierda'
        elif en_borde_derecho:
            return 'borde_derecho'
        elif en_borde_izquierdo:
            return 'borde_izquierdo'
        elif en_borde_inferior:
            return 'borde_inferior'
        elif en_borde_superior:
            return 'borde_superior'
        else:
            return None
    
    def mousePressEvent(self, event):
        """Permite mover la ventana arrastrando o redimensionar"""
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            borde = self.detectar_borde_resize(pos)
            
            if borde:
                # Iniciar redimensionamiento
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.resize_start_size = QPoint(self.width(), self.height())
                self.resize_start_window_pos = self.pos()
                self.resize_corner = borde
                self.old_pos = None
            elif pos.x() > 30 or pos.y() > 30:
                # Mover la ventana
                self.old_pos = event.globalPos()
                self.resizing = False
            else:
                # Clic en el botón expandir
                self.old_pos = None
                self.resizing = False
                
    def mouseMoveEvent(self, event):
        """Mueve la ventana cuando se arrastra o redimensiona"""
        if self.resizing and self.resize_start_pos and self.resize_start_window_pos:
            # Redimensionar
            delta = event.globalPos() - self.resize_start_pos
            nuevo_ancho = self.resize_start_size.x()
            nuevo_alto = self.resize_start_size.y()
            nueva_x = self.resize_start_window_pos.x()
            nueva_y = self.resize_start_window_pos.y()
            
            if self.resize_corner in ['borde_derecho', 'esquina_inferior_derecha', 'esquina_superior_derecha']:
                nuevo_ancho = max(100, min(800, self.resize_start_size.x() + delta.x()))
            elif self.resize_corner in ['borde_izquierdo', 'esquina_inferior_izquierda', 'esquina_superior_izquierda']:
                nuevo_ancho = max(100, min(800, self.resize_start_size.x() - delta.x()))
                nueva_x = self.resize_start_window_pos.x() + delta.x()
            
            if self.resize_corner in ['borde_inferior', 'esquina_inferior_derecha', 'esquina_inferior_izquierda']:
                nuevo_alto = max(40, min(600, self.resize_start_size.y() + delta.y()))
            elif self.resize_corner in ['borde_superior', 'esquina_superior_derecha', 'esquina_superior_izquierda']:
                nuevo_alto = max(40, min(600, self.resize_start_size.y() - delta.y()))
                nueva_y = self.resize_start_window_pos.y() + delta.y()
            
            # Ajustar posición si se redimensiona desde izquierda o arriba
            if self.resize_corner in ['borde_izquierdo', 'esquina_inferior_izquierda', 'esquina_superior_izquierda']:
                # Asegurar que el ancho mínimo no cause que se salga de la pantalla
                if nuevo_ancho < 100:
                    nuevo_ancho = 100
                    nueva_x = self.resize_start_window_pos.x() + (self.resize_start_size.x() - 100)
            
            if self.resize_corner in ['borde_superior', 'esquina_superior_derecha', 'esquina_superior_izquierda']:
                # Asegurar que el alto mínimo no cause que se salga de la pantalla
                if nuevo_alto < 40:
                    nuevo_alto = 40
                    nueva_y = self.resize_start_window_pos.y() + (self.resize_start_size.y() - 40)
            
            # Aplicar cambios
            self.resize(nuevo_ancho, nuevo_alto)
            if self.resize_corner in ['borde_izquierdo', 'borde_superior', 'esquina_inferior_izquierda', 
                                     'esquina_superior_derecha', 'esquina_superior_izquierda']:
                self.move(nueva_x, nueva_y)
            
            # Actualizar título para que se ajuste al nuevo tamaño
            self.actualizar_titulo()
            
            # Guardar tamaño personalizado según el estado
            if self.expandida:
                self.tamano_personalizado_expandido = (nuevo_ancho, nuevo_alto)
            else:
                self.tamano_personalizado_colapsado = (nuevo_ancho, nuevo_alto)
            if self.parent_app:
                self.parent_app.guardar_tamano_casilla(self.nombre, (nuevo_ancho, nuevo_alto), self.expandida)
        elif self.old_pos:
            # Mover la ventana
            delta = event.globalPos() - self.old_pos
            nueva_pos = self.pos() + delta
            # Limitar la posición dentro de los bordes de la pantalla
            nueva_pos = self.limitar_a_pantalla(nueva_pos)
            # Evitar colisiones con otras casillas
            nueva_pos = self.evitar_colisiones(nueva_pos)
            self.move(nueva_pos)
            self.old_pos = event.globalPos()
            # Guardar posición
            if self.parent_app:
                self.parent_app.guardar_posicion_casilla(self.nombre, self.pos())
        else:
            # Cambiar cursor cuando está sobre el área de redimensionamiento
            borde = self.detectar_borde_resize(event.pos())
            if borde:
                if borde in ['esquina_inferior_derecha', 'esquina_superior_izquierda']:
                    self.setCursor(Qt.SizeFDiagCursor)
                elif borde in ['esquina_inferior_izquierda', 'esquina_superior_derecha']:
                    self.setCursor(Qt.SizeBDiagCursor)
                elif borde in ['borde_izquierdo', 'borde_derecho']:
                    self.setCursor(Qt.SizeHorCursor)
                elif borde in ['borde_superior', 'borde_inferior']:
                    self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def actualizar_tamano_iconos(self):
        """Actualiza el tamaño de los iconos en la lista"""
        self.lista_archivos.setIconSize(QSize(self.tamano_iconos, self.tamano_iconos))
        # Si está en modo cuadrícula, actualizar el tamaño de la cuadrícula
        if self.tipo_vista == "cuadricula":
            tamano_cuadricula = max(self.tamano_iconos + 80, 120)
            self.lista_archivos.setGridSize(QSize(tamano_cuadricula, tamano_cuadricula))
        # Guardar el tamaño de iconos si hay una app padre
        if self.parent_app:
            self.parent_app.guardar_tamano_iconos(self.nombre, self.tamano_iconos)
    
    def actualizar_velocidad_scroll(self):
        """Actualiza la velocidad de scroll según la configuración"""
        scrollbar = self.lista_archivos.verticalScrollBar()
        if scrollbar:
            # Calcular singleStep basado en porcentaje (100% = 20 píxeles)
            single_step_base = 20
            single_step = int(single_step_base * (self.velocidad_scroll / 100.0))
            scrollbar.setSingleStep(max(1, single_step))
    
    def calcular_porcentaje_iconos(self, tamano):
        """Calcula el porcentaje del tamaño de iconos (16px = 0%, 64px = 100%)"""
        rango_min = 16
        rango_max = 64
        rango_total = rango_max - rango_min
        porcentaje = ((tamano - rango_min) / rango_total) * 100
        return round(porcentaje, 1)
    
    def cambiar_tamano_iconos_porcentaje(self, incremento_porcentaje):
        """Cambia el tamaño de los iconos en porcentaje (positivo para aumentar, negativo para disminuir)"""
        rango_min = 16
        rango_max = 64
        rango_total = rango_max - rango_min
        
        # Calcular porcentaje actual
        porcentaje_actual = self.calcular_porcentaje_iconos(self.tamano_iconos)
        
        # Aplicar incremento en porcentaje
        nuevo_porcentaje = max(0, min(100, porcentaje_actual + incremento_porcentaje))
        
        # Convertir porcentaje a píxeles
        nuevo_tamano = rango_min + (nuevo_porcentaje / 100) * rango_total
        nuevo_tamano = round(nuevo_tamano)
        
        # Limitar entre 16 y 64 píxeles
        nuevo_tamano = max(16, min(64, nuevo_tamano))
        
        if nuevo_tamano != self.tamano_iconos:
            self.tamano_iconos = nuevo_tamano
            self.actualizar_tamano_iconos()
            # Actualizar la lista para aplicar el nuevo tamaño
            self.actualizar_lista_archivos()
            # Mostrar porcentaje
            self.mostrar_porcentaje_iconos()
    
    def mostrar_porcentaje_iconos(self):
        """Muestra temporalmente el porcentaje del tamaño de iconos"""
        porcentaje = self.calcular_porcentaje_iconos(self.tamano_iconos)
        
        # Crear o actualizar el label
        if self.label_porcentaje is None:
            self.label_porcentaje = QLabel(self)
            self.label_porcentaje.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 200);
                    color: white;
                    border: 2px solid rgba(100, 150, 200, 255);
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.label_porcentaje.setAlignment(Qt.AlignCenter)
            self.label_porcentaje.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
            self.label_porcentaje.setAttribute(Qt.WA_TranslucentBackground)
        
        self.label_porcentaje.setText(f"Tamaño de iconos: {porcentaje}%")
        self.label_porcentaje.adjustSize()
        
        # Posicionar el label cerca del cursor o en el centro de la casilla
        pos_global = self.mapToGlobal(QPoint(self.width() // 2 - self.label_porcentaje.width() // 2, 20))
        self.label_porcentaje.move(pos_global)
        self.label_porcentaje.show()
        self.label_porcentaje.raise_()
        
        # Ocultar después de 1.5 segundos
        if self.timer_porcentaje:
            self.timer_porcentaje.stop()
        
        self.timer_porcentaje = QTimer()
        self.timer_porcentaje.timeout.connect(self.ocultar_porcentaje)
        self.timer_porcentaje.setSingleShot(True)
        self.timer_porcentaje.start(1500)
    
    def ocultar_porcentaje(self):
        """Oculta el label de porcentaje"""
        if self.label_porcentaje:
            self.label_porcentaje.hide()
    
    def cambiar_tamano_iconos(self, incremento):
        """Cambia el tamaño de los iconos (positivo para aumentar, negativo para disminuir) - DEPRECADO, usar cambiar_tamano_iconos_porcentaje"""
        nuevo_tamano = self.tamano_iconos + incremento
        # Limitar entre 16 y 64 píxeles
        nuevo_tamano = max(16, min(64, nuevo_tamano))
        if nuevo_tamano != self.tamano_iconos:
            self.tamano_iconos = nuevo_tamano
            self.actualizar_tamano_iconos()
            # Actualizar la lista para aplicar el nuevo tamaño
            self.actualizar_lista_archivos()
    
    def wheelEvent(self, event):
        """Maneja el scroll con la rueda del mouse"""
        # Si la casilla está expandida y la lista de archivos es visible
        if self.expandida and self.lista_archivos.isVisible():
            # Usar coordenadas globales para mayor precisión
            global_pos = event.globalPos()
            
            # Obtener el rectángulo de la lista en coordenadas globales
            lista_global_rect = self.lista_archivos.geometry()
            lista_global_top_left = self.lista_archivos.mapToGlobal(QPoint(0, 0))
            lista_global_bottom_right = self.lista_archivos.mapToGlobal(
                QPoint(lista_global_rect.width(), lista_global_rect.height())
            )
            
            # Verificar si el mouse está sobre la lista usando coordenadas globales
            if (lista_global_top_left.x() <= global_pos.x() <= lista_global_bottom_right.x() and
                lista_global_top_left.y() <= global_pos.y() <= lista_global_bottom_right.y()):
                
                # Si se presiona Ctrl, cambiar el tamaño de los iconos en porcentaje
                if event.modifiers() & Qt.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta != 0:
                        # Usar incremento de 5% por movimiento de rueda
                        incremento_porcentaje = 5.0 if delta > 0 else -5.0
                        self.cambiar_tamano_iconos_porcentaje(incremento_porcentaje)
                        event.accept()
                        return
                
                # Convertir coordenadas al QListWidget
                pos_en_lista = self.lista_archivos.mapFromGlobal(global_pos)
                
                # Obtener el scrollbar y hacer scroll directamente
                scrollbar = self.lista_archivos.verticalScrollBar()
                if scrollbar:
                    # Calcular multiplicadores basados en la velocidad configurada (100% = valores base)
                    multiplicador_pixel = 2.0 * (self.velocidad_scroll / 100.0)
                    divisor_angle = 8.0 / (self.velocidad_scroll / 100.0)
                    
                    # Preferir pixelDelta para scroll (disponible en trackpads y ratones de alta precisión)
                    if event.pixelDelta().y() != 0:
                        # Usar pixelDelta con multiplicador según velocidad configurada
                        scroll_amount = -event.pixelDelta().y() * multiplicador_pixel
                    else:
                        # Usar angleDelta con divisor según velocidad configurada
                        delta = event.angleDelta().y()
                        scroll_amount = -delta / divisor_angle
                    
                    if scroll_amount != 0:
                        # Calcular el nuevo valor del scroll
                        current_value = scrollbar.value()
                        new_value = current_value + scroll_amount
                        # Limitar el valor dentro del rango válido
                        new_value = max(scrollbar.minimum(), min(scrollbar.maximum(), new_value))
                        scrollbar.setValue(new_value)
                        event.accept()
                        return
                
                # Si no hay scrollbar o no funcionó, intentar enviar el evento directamente
                wheel_event = QWheelEvent(
                    pos_en_lista,
                    event.globalPos(),
                    event.pixelDelta(),
                    event.angleDelta(),
                    event.buttons(),
                    event.modifiers(),
                    event.phase(),
                    event.inverted()
                )
                result = QApplication.sendEvent(self.lista_archivos, wheel_event)
                if result:
                    event.accept()
                    return
        
        # Si no está sobre la lista, no hacer nada
        super().wheelEvent(event)
    
    def detectar_colision(self, posicion, otra_casilla):
        """Detecta si esta casilla colisiona con otra casilla"""
        if otra_casilla == self or not otra_casilla.isVisible():
            return False
        
        x1, y1 = posicion.x(), posicion.y()
        w1, h1 = self.width(), self.height()
        
        x2, y2 = otra_casilla.pos().x(), otra_casilla.pos().y()
        w2, h2 = otra_casilla.width(), otra_casilla.height()
        
        # Verificar si hay superposición (con un margen mínimo de 5px)
        margen = 5
        return not (x1 + w1 + margen < x2 or 
                   x2 + w2 + margen < x1 or 
                   y1 + h1 + margen < y2 or 
                   y2 + h2 + margen < y1)
    
    def evitar_colisiones(self, posicion):
        """Ajusta la posición para evitar colisiones con otras casillas"""
        if not self.parent_app:
            return posicion
        
        nueva_pos = QPoint(posicion.x(), posicion.y())
        intentos = 0
        max_intentos = 50
        
        # Intentar encontrar una posición sin colisiones
        while intentos < max_intentos:
            colision = False
            for nombre, otra_casilla in self.parent_app.casillas.items():
                if self.detectar_colision(nueva_pos, otra_casilla):
                    colision = True
                    # Calcular dirección de empuje
                    otra_pos = otra_casilla.pos()
                    dx = nueva_pos.x() - otra_pos.x()
                    dy = nueva_pos.y() - otra_pos.y()
                    
                    # Si están muy cerca, empujar en la dirección del movimiento
                    if abs(dx) < abs(dy):
                        # Empujar verticalmente
                        if dy > 0:
                            nueva_pos.setY(otra_pos.y() + otra_casilla.height() + 5)
                        else:
                            nueva_pos.setY(otra_pos.y() - self.height() - 5)
                    else:
                        # Empujar horizontalmente
                        if dx > 0:
                            nueva_pos.setX(otra_pos.x() + otra_casilla.width() + 5)
                        else:
                            nueva_pos.setX(otra_pos.x() - self.width() - 5)
                    
                    # Asegurar que sigue dentro de la pantalla
                    nueva_pos = self.limitar_a_pantalla(nueva_pos)
                    break
            
            if not colision:
                break
            
            intentos += 1
        
        return nueva_pos
    
    def limitar_a_pantalla(self, posicion):
        """Ajusta la posición para que la casilla esté dentro de los límites de la pantalla"""
        screen = QApplication.primaryScreen().geometry()
        x, y = posicion.x(), posicion.y()
        ancho = self.width()
        alto = self.height()
        
        # Limitar en X
        if x < 0:
            x = 0
        elif x + ancho > screen.width():
            x = screen.width() - ancho
        
        # Limitar en Y
        if y < 0:
            y = 0
        elif y + alto > screen.height():
            y = screen.height() - alto
        
        return QPoint(x, y)
            
    def mouseReleaseEvent(self, event):
        """Libera la posición al soltar el mouse"""
        # Si se estaba redimensionando, guardar el tamaño final
        if self.resizing and self.parent_app:
            if self.expandida:
                self.tamano_personalizado_expandido = (self.width(), self.height())
                self.parent_app.guardar_tamano_casilla(self.nombre, self.tamano_personalizado_expandido, True)
            else:
                self.tamano_personalizado_colapsado = (self.width(), self.height())
                self.parent_app.guardar_tamano_casilla(self.nombre, self.tamano_personalizado_colapsado, False)
        
        self.old_pos = None
        self.resizing = False
        self.resize_start_pos = None
        self.resize_start_size = None
        self.resize_start_window_pos = None
        self.resize_corner = None
        self.setCursor(Qt.ArrowCursor)
        
    def dragLeaveEvent(self, event):
        """Se ejecuta cuando se sale del área de la casilla"""
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 150, 200, 140);
                border: 2px solid rgba(50, 100, 150, 220);
                border-radius: 12px;
            }
        """)
        
    def dropEvent(self, event: QDropEvent):
        """Se ejecuta cuando se suelta un archivo en la casilla"""
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 150, 200, 140);
                border: 2px solid rgba(50, 100, 150, 220);
                border-radius: 12px;
            }
        """)
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                archivo_path = url.toLocalFile()
                if os.path.exists(archivo_path):
                    elemento = Path(archivo_path)
                    
                    # Verificar si el archivo viene de esta misma casilla (no mover)
                    if elemento.parent == self.carpeta_path:
                        # El archivo ya está en esta casilla, no hacer nada
                        event.ignore()
                        return
                    
                    # Verificar si viene de otra casilla
                    if self.parent_app:
                        # Buscar en qué casilla está el archivo
                        casilla_origen = None
                        for nombre, casilla in self.parent_app.casillas.items():
                            if elemento.parent == casilla.carpeta_path:
                                casilla_origen = casilla
                                break
                        
                        # Si viene de otra casilla, mover entre casillas
                        if casilla_origen and casilla_origen != self:
                            self.parent_app.mover_archivo_entre_casillas(archivo_path, casilla_origen.nombre, self.nombre)
                        else:
                            # Viene del escritorio u otra ubicación, mover a esta casilla
                            self.archivo_soltado.emit(archivo_path, self.nombre)
            
            # Actualizar lista después de mover archivo
            self.actualizar_lista_archivos()
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Se ejecuta cuando se arrastra algo sobre la casilla"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(120, 180, 230, 200);
                    border: 3px solid rgba(70, 130, 200, 255);
                    border-radius: 12px;
                }
            """)
        else:
            event.ignore()
    
    def toggle_expandir(self):
        """Expande o colapsa la casilla para mostrar/ocultar archivos"""
        self.expandida = not self.expandida
        
        if self.expandida:
            # Expandir - mantener posición superior, crecer hacia abajo
            pos_actual = self.pos()
            
            # Usar tamaño personalizado expandido si existe, sino usar el expandido por defecto
            if self.tamano_personalizado_expandido:
                nuevo_ancho, nuevo_alto = self.tamano_personalizado_expandido
            else:
                nuevo_ancho = self.tamano_expandido[0]
                nuevo_alto = self.tamano_expandido[1]
            
            # Mantener la posición Y (superior) y ajustar solo el tamaño
            self.resize(nuevo_ancho, nuevo_alto)
            self.move(pos_actual.x(), pos_actual.y())  # Mantener posición superior
            
            # Permitir que la lista se ajuste dinámicamente al tamaño de la casilla
            # El tamaño mínimo será suficiente para mostrar algunos elementos
            self.lista_archivos.setMinimumHeight(100)
            self.lista_archivos.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.lista_archivos.setVisible(True)
            # Forzar actualización del layout para que la lista tenga el tamaño correcto
            QApplication.processEvents()
            self.btn_expandir.setText("▲")
            
            # Mostrar contador cuando está expandida
            self.contador_widget.setVisible(True)
            
            # Actualizar título
            self.actualizar_titulo()
            
            # Forzar actualización del layout antes de mover casillas
            QApplication.processEvents()
            
            # Mover casillas que están siendo tapadas
            self.mover_casillas_tapadas()
        else:
            # Colapsar - restaurar posiciones originales
            self.restaurar_posiciones_originales()
            
            pos_actual = self.pos()
            # Usar tamaño personalizado colapsado si existe, sino usar el colapsado por defecto
            if self.tamano_personalizado_colapsado:
                nuevo_ancho, nuevo_alto = self.tamano_personalizado_colapsado
            else:
                nuevo_ancho = self.tamano_colapsado[0]
                nuevo_alto = self.tamano_colapsado[1]
            
            # Mantener la posición Y (superior) y ajustar solo el tamaño
            self.resize(nuevo_ancho, nuevo_alto)
            self.move(pos_actual.x(), pos_actual.y())  # Mantener posición superior
            
            self.lista_archivos.setMinimumHeight(0)
            self.lista_archivos.setMaximumHeight(0)
            self.lista_archivos.setVisible(False)
            self.btn_expandir.setText("▼")
            
            # Ocultar contador cuando está colapsada
            self.contador_widget.setVisible(False)
            
            # Actualizar título
            self.actualizar_titulo()
        
        # Ajustar posición después de cambiar tamaño para que esté dentro de la pantalla y sin colisiones
        pos_actual = self.pos()
        pos_ajustada = self.limitar_a_pantalla(pos_actual)
        pos_ajustada = self.evitar_colisiones(pos_ajustada)
        if pos_ajustada != pos_actual:
            self.move(pos_ajustada)
        
        # Guardar posición y tamaño después de cambiar tamaño
        if self.parent_app:
            self.parent_app.guardar_posicion_casilla(self.nombre, self.pos())
            # Guardar también el tamaño actual según el estado
            if self.expandida and self.tamano_personalizado_expandido:
                self.parent_app.guardar_tamano_casilla(self.nombre, self.tamano_personalizado_expandido, True)
            elif not self.expandida and self.tamano_personalizado_colapsado:
                self.parent_app.guardar_tamano_casilla(self.nombre, self.tamano_personalizado_colapsado, False)
    
    def mover_casillas_tapadas(self):
        """Mueve las casillas que están siendo tapadas por esta casilla expandida"""
        if not self.parent_app:
            return
        
        # Limpiar posiciones guardadas anteriormente
        self.posiciones_originales.clear()
        
        mi_x, mi_y = self.pos().x(), self.pos().y()
        mi_ancho, mi_alto = self.width(), self.height()
        mi_bottom = mi_y + mi_alto  # Parte inferior de esta casilla expandida
        
        # Verificar todas las otras casillas
        for nombre, otra_casilla in self.parent_app.casillas.items():
            if otra_casilla == self or not otra_casilla.isVisible():
                continue
            
            otra_x, otra_y = otra_casilla.pos().x(), otra_casilla.pos().y()
            otra_ancho, otra_alto = otra_casilla.width(), otra_casilla.height()
            otra_bottom = otra_y + otra_alto
            
            # Verificar si hay superposición horizontal (misma columna)
            hay_superposicion_horizontal = not (mi_x + mi_ancho <= otra_x or otra_x + otra_ancho <= mi_x)
            
            # Verificar si la otra casilla está siendo tapada
            # Está siendo tapada si:
            # 1. Hay superposición horizontal (están en la misma columna)
            # 2. La parte superior de la otra casilla está dentro del rango vertical de esta casilla expandida
            #    (es decir, otra_y está entre mi_y y mi_bottom)
            # 3. La otra casilla NO está completamente arriba de esta (su parte inferior no está arriba de mi parte superior)
            esta_siendo_tapada = (hay_superposicion_horizontal and 
                                 otra_y >= mi_y and 
                                 otra_y < mi_bottom and
                                 otra_bottom > mi_y)  # Asegurar que hay alguna superposición real
            
            # Si está siendo tapada, moverla hacia abajo
            if esta_siendo_tapada:
                # Guardar posición original antes de mover (solo si no estaba ya guardada)
                if nombre not in self.posiciones_originales:
                    pos_original = otra_casilla.pos()
                    self.posiciones_originales[nombre] = QPoint(pos_original.x(), pos_original.y())
                
                # Calcular nueva posición: mover hacia abajo justo debajo de esta casilla
                nueva_y = mi_bottom + 10  # 10 píxeles de margen
                nueva_pos = QPoint(otra_x, nueva_y)
                
                # Asegurar que esté dentro de la pantalla
                nueva_pos = otra_casilla.limitar_a_pantalla(nueva_pos)
                
                # Mover la casilla
                otra_casilla.move(nueva_pos)
                
                # NO guardar la posición temporal en el archivo (solo se guardará cuando se restaure)
    
    def restaurar_posiciones_originales(self):
        """Restaura las posiciones originales de las casillas que fueron movidas"""
        if not self.parent_app:
            return
        
        # Restaurar cada casilla a su posición original
        for nombre, pos_original in self.posiciones_originales.items():
            if nombre in self.parent_app.casillas:
                casilla = self.parent_app.casillas[nombre]
                # Mover directamente a la posición original
                casilla.move(pos_original)
                # Guardar la posición restaurada
                if casilla.parent_app:
                    casilla.parent_app.guardar_posicion_casilla(nombre, pos_original)
        
        # Limpiar las posiciones guardadas
        self.posiciones_originales.clear()
    
    def mover_para_evitar(self, casilla_obstaculo):
        """Calcula una nueva posición para esta casilla para evitar ser tapada por otra"""
        mi_pos = self.pos()
        obstaculo_pos = casilla_obstaculo.pos()
        obstaculo_ancho = casilla_obstaculo.width()
        obstaculo_alto = casilla_obstaculo.height()
        
        mi_x, mi_y = mi_pos.x(), mi_pos.y()
        mi_ancho, mi_alto = self.width(), self.height()
        
        obstaculo_x, obstaculo_y = obstaculo_pos.x(), obstaculo_pos.y()
        obstaculo_derecha = obstaculo_x + obstaculo_ancho
        obstaculo_abajo = obstaculo_y + obstaculo_alto
        
        # Calcular distancias en cada dirección
        distancia_izquierda = abs(mi_x + mi_ancho - obstaculo_x)
        distancia_derecha = abs(obstaculo_derecha - mi_x)
        distancia_arriba = abs(mi_y + mi_alto - obstaculo_y)
        distancia_abajo = abs(obstaculo_abajo - mi_y)
        
        # Encontrar la dirección con menor distancia para mover
        distancias = [
            (distancia_izquierda, 'izquierda'),
            (distancia_derecha, 'derecha'),
            (distancia_arriba, 'arriba'),
            (distancia_abajo, 'abajo')
        ]
        distancias.sort(key=lambda x: x[0])
        
        nueva_pos = QPoint(mi_x, mi_y)
        margen = 5
        
        # Mover en la dirección más cercana
        if distancias[0][1] == 'derecha':
            # Mover a la derecha del obstáculo
            nueva_pos.setX(obstaculo_derecha + margen)
        elif distancias[0][1] == 'izquierda':
            # Mover a la izquierda del obstáculo
            nueva_pos.setX(obstaculo_x - mi_ancho - margen)
        elif distancias[0][1] == 'abajo':
            # Mover debajo del obstáculo
            nueva_pos.setY(obstaculo_abajo + margen)
        elif distancias[0][1] == 'arriba':
            # Mover arriba del obstáculo
            nueva_pos.setY(obstaculo_y - mi_alto - margen)
        
        # Asegurar que esté dentro de la pantalla
        nueva_pos = self.limitar_a_pantalla(nueva_pos)
        
        # Verificar que no colisione con otras casillas (excepto la que está evitando)
        nueva_pos = self.evitar_colisiones_excepto(nueva_pos, casilla_obstaculo)
        
        return nueva_pos
    
    def evitar_colisiones_excepto(self, posicion, excepcion):
        """Ajusta la posición para evitar colisiones con otras casillas, excepto una específica"""
        if not self.parent_app:
            return posicion
        
        nueva_pos = QPoint(posicion.x(), posicion.y())
        intentos = 0
        max_intentos = 50
        
        while intentos < max_intentos:
            colision = False
            for nombre, otra_casilla in self.parent_app.casillas.items():
                if otra_casilla == self or otra_casilla == excepcion or not otra_casilla.isVisible():
                    continue
                
                if self.detectar_colision(nueva_pos, otra_casilla):
                    colision = True
                    otra_pos = otra_casilla.pos()
                    dx = nueva_pos.x() - otra_pos.x()
                    dy = nueva_pos.y() - otra_pos.y()
                    
                    if abs(dx) < abs(dy):
                        if dy > 0:
                            nueva_pos.setY(otra_pos.y() + otra_casilla.height() + 5)
                        else:
                            nueva_pos.setY(otra_pos.y() - self.height() - 5)
                    else:
                        if dx > 0:
                            nueva_pos.setX(otra_pos.x() + otra_casilla.width() + 5)
                        else:
                            nueva_pos.setX(otra_pos.x() - self.width() - 5)
                    
                    nueva_pos = self.limitar_a_pantalla(nueva_pos)
                    break
            
            if not colision:
                break
            
            intentos += 1
        
        return nueva_pos
    
    def actualizar_lista_archivos(self):
        """Actualiza la lista de archivos y carpetas en la casilla"""
        self.lista_archivos.clear()
        
        # Asegurar que carpeta_path sea Path
        carpeta = Path(self.carpeta_path) if not isinstance(self.carpeta_path, Path) else self.carpeta_path
        
        if not carpeta.exists():
            self.label_contador.setText("0 elementos")
            return
        
        elementos = []
        try:
            for item in carpeta.iterdir():
                # Incluir tanto archivos como carpetas
                elementos.append(item)
        except Exception as e:
            print(f"Error al leer elementos de {carpeta}: {e}")
            self.label_contador.setText("Error")
            return
        
        # Ordenar: primero carpetas, luego archivos, ambos alfabéticamente
        carpetas = [e for e in elementos if e.is_dir()]
        archivos = [e for e in elementos if e.is_file()]
        carpetas.sort(key=lambda x: x.name.lower())
        archivos.sort(key=lambda x: x.name.lower())
        elementos_ordenados = carpetas + archivos
        
        # Crear proveedor de iconos
        icon_provider = QFileIconProvider()
        
        # Tamaño deseado para los iconos (usar un tamaño mayor para mejor calidad al escalar)
        tamano_icono_deseado = QSize(self.tamano_iconos, self.tamano_iconos)
        # Obtener el icono en un tamaño mayor para mejor calidad (usar multiplicador configurado)
        multiplicador = getattr(self, 'multiplicador_resolucion_iconos', 2.0)
        tamano_icono_alta_calidad = QSize(
            int(self.tamano_iconos * multiplicador), 
            int(self.tamano_iconos * multiplicador)
        )
        
        # Agregar a la lista con iconos reales
        for elemento in elementos_ordenados:
            if elemento.is_dir():
                # Carpeta: usar icono de carpeta
                nombre = elemento.name
                file_info = QFileInfo(str(elemento))
                icono_original = icon_provider.icon(file_info)
            else:
                # Archivo: obtener icono según el tipo
                nombre = elemento.name
                ruta_archivo = str(elemento)
                
                # Para archivos .lnk, .url, .ink (atajos), intentar obtener el icono del destino
                if elemento.suffix.lower() in ['lnk', 'url', 'ink']:
                    try:
                        # Intentar obtener el icono del archivo destino
                        file_info = QFileInfo(ruta_archivo)
                        icono_original = icon_provider.icon(file_info)
                    except:
                        # Si falla, usar icono genérico
                        file_info = QFileInfo(ruta_archivo)
                        icono_original = icon_provider.icon(QFileIconProvider.File)
                else:
                    # Para otros archivos, usar el icono del sistema
                    file_info = QFileInfo(ruta_archivo)
                    icono_original = icon_provider.icon(file_info)
            
            # Obtener el pixmap en alta calidad y escalarlo suavemente
            pixmap_alta_calidad = icono_original.pixmap(tamano_icono_alta_calidad)
            # Escalar suavemente al tamaño deseado para mejor calidad
            pixmap_final = pixmap_alta_calidad.scaled(
                tamano_icono_deseado,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            # Crear un nuevo icono con el pixmap de alta calidad
            icono_mejorado = QIcon(pixmap_final)
            
            item = QListWidgetItem(icono_mejorado, nombre)
            item.setData(Qt.UserRole, str(elemento))
            # Habilitar drag para este item
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled)
            self.lista_archivos.addItem(item)
        
        # Actualizar contador
        num_carpetas = len(carpetas)
        num_archivos = len(archivos)
        total = num_carpetas + num_archivos
        
        if total == 0:
            self.label_contador.setText("0 elementos")
        elif total == 1:
            if num_carpetas == 1:
                self.label_contador.setText("1 carpeta")
            else:
                self.label_contador.setText("1 archivo")
        else:
            if num_carpetas > 0 and num_archivos > 0:
                self.label_contador.setText(f"{num_carpetas} carpeta{'s' if num_carpetas > 1 else ''}, {num_archivos} archivo{'s' if num_archivos > 1 else ''}")
            elif num_carpetas > 0:
                self.label_contador.setText(f"{num_carpetas} carpetas")
            else:
                self.label_contador.setText(f"{num_archivos} archivos")
        
        # Asegurar que la barra de scroll se actualice correctamente
        if self.expandida and self.lista_archivos.isVisible():
            QApplication.processEvents()
            # Forzar actualización del scrollbar
            scrollbar = self.lista_archivos.verticalScrollBar()
            if scrollbar:
                scrollbar.update()
                # Asegurar que la política de scroll esté activa
                self.lista_archivos.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Aplicar tipo de vista después de actualizar
        self.aplicar_tipo_vista()
    
    def iniciar_drag_archivo(self, supportedActions):
        """Inicia el arrastre de un archivo desde la lista"""
        items = self.lista_archivos.selectedItems()
        if not items:
            return
        
        item = items[0]
        ruta_archivo = item.data(Qt.UserRole)
        
        if ruta_archivo and os.path.exists(ruta_archivo):
            elemento = Path(ruta_archivo)
            ruta_original = str(elemento)
            
            # Crear MIME data con la URL del archivo
            mime_data = QMimeData()
            url = QUrl.fromLocalFile(ruta_archivo)
            mime_data.setUrls([url])
            
            # Crear el drag object
            drag = QDrag(self.lista_archivos)
            drag.setMimeData(mime_data)
            
            # Usar el icono del item como imagen de arrastre
            icono = item.icon()
            if not icono.isNull():
                pixmap = icono.pixmap(32, 32)
                drag.setPixmap(pixmap)
                drag.setHotSpot(QPoint(16, 16))
            
            # Ejecutar el drag
            result = drag.exec_(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)
            
            # Verificar si el archivo fue movido (ya no existe en la ubicación original)
            # Esto cubre tanto el caso de mover a otra casilla como al escritorio
            QApplication.processEvents()
            if not os.path.exists(ruta_original):
                # El archivo fue movido, actualizar la lista
                self.actualizar_lista_archivos()
            elif result == Qt.MoveAction:
                # Si el drag retornó MoveAction pero el archivo aún existe,
                # podría haber sido movido a otra casilla (el dropEvent lo maneja)
                # Solo actualizamos la lista por si acaso
                QApplication.processEvents()
                self.actualizar_lista_archivos()
    
    def aplicar_tipo_vista(self):
        """Aplica el tipo de vista configurado a la lista"""
        if self.tipo_vista == "cuadricula":
            # Vista de cuadrícula (iconos)
            self.lista_archivos.setViewMode(QListWidget.IconMode)
            self.lista_archivos.setResizeMode(QListWidget.Adjust)
            # Calcular tamaño de cuadrícula basado en el tamaño de iconos
            # Asegurar espacio suficiente para icono + texto + padding
            tamano_cuadricula = max(self.tamano_iconos + 80, 120)  # Espacio para icono + texto + padding
            self.lista_archivos.setGridSize(QSize(tamano_cuadricula, tamano_cuadricula))
            self.lista_archivos.setSpacing(8)
            # Mostrar texto debajo del icono
            self.lista_archivos.setWordWrap(True)
        else:
            # Vista de lista (mantener configuración original, sin cambios)
            self.lista_archivos.setViewMode(QListWidget.ListMode)
            # Limpiar configuraciones de cuadrícula para volver a la apariencia original
            # No establecer resizeMode ni spacing para mantener los valores por defecto
            # Solo resetear el gridSize si estaba configurado
            self.lista_archivos.setGridSize(QSize(-1, -1))  # Resetear tamaño de cuadrícula
            self.lista_archivos.setWordWrap(False)  # Asegurar que no haya word wrap
    
    def abrir_archivo(self, item):
        """Abre el archivo o carpeta seleccionado"""
        ruta_elemento = item.data(Qt.UserRole)
        if ruta_elemento and os.path.exists(ruta_elemento):
            try:
                elemento = Path(ruta_elemento)
                if elemento.is_dir():
                    # Abrir carpeta en el explorador
                    os.startfile(str(elemento))  # Windows
                else:
                    # Abrir archivo
                    os.startfile(ruta_elemento)  # Windows
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo abrir: {str(e)}")
            
    def eliminar_casilla(self):
        """Elimina la casilla"""
        respuesta = QMessageBox.question(
            self, 
            "Confirmar eliminación",
            f"¿Eliminar la casilla '{self.nombre}'?\n\nNota: La carpeta no se eliminará.",
            QMessageBox.Yes | QMessageBox.No
        )
        if respuesta == QMessageBox.Yes:
            self.casilla_eliminada.emit(self)
            self.close()


class DialogCrearCasilla(QDialog):
    """Diálogo para crear una nueva casilla"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nombre_casilla = None
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Crear Nueva Casilla")
        self.setFixedSize(400, 140)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Label e input
        label = QLabel("Nombre de la casilla:")
        label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #333;
            }
        """)
        
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Ej: Trabajo, Juegos, Documentos...")
        self.input_nombre.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 11px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid rgba(100, 150, 200, 200);
            }
        """)
        self.input_nombre.returnPressed.connect(self.aceptar)
        self.input_nombre.setFocus()
        
        # Botones
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.aceptar)
        botones.rejected.connect(self.reject)
        
        btn_ok = botones.button(QDialogButtonBox.Ok)
        btn_ok.setText("Crear")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 150, 200, 220);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 11px;
                font-weight: bold;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: rgba(120, 170, 220, 240);
            }
        """)
        
        btn_cancel = botones.button(QDialogButtonBox.Cancel)
        btn_cancel.setText("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                color: #333;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 11px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #d8d8d8;
            }
        """)
        
        layout.addWidget(label)
        layout.addWidget(self.input_nombre)
        layout.addWidget(botones)
        
        self.setLayout(layout)
        
    def aceptar(self):
        """Acepta el diálogo y guarda el nombre"""
        nombre = self.input_nombre.text().strip()
        if nombre:
            self.nombre_casilla = nombre
            self.accept()
        else:
            QMessageBox.warning(self, "Advertencia", "Por favor ingresa un nombre para la casilla.")


def obtener_ruta_fondo_escritorio():
    """Obtiene la ruta del fondo de escritorio de Windows"""
    try:
        # Intentar obtener desde el registro de Windows
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop"
        )
        try:
            # Obtener el valor del fondo
            wallpaper_path, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)
            
            # Expandir variables de entorno si es necesario
            wallpaper_path = os.path.expandvars(wallpaper_path)
            
            if os.path.exists(wallpaper_path):
                return wallpaper_path
        except:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error al obtener fondo de escritorio: {e}")
    
    return None


def analizar_colores_imagen(ruta_imagen, num_colores=5):
    """Analiza una imagen y extrae los colores dominantes"""
    try:
        imagen = QImage(ruta_imagen)
        if imagen.isNull():
            return None
        
        # Redimensionar para análisis más rápido (máximo 200x200)
        if imagen.width() > 200 or imagen.height() > 200:
            imagen = imagen.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Obtener colores de píxeles (muestrear cada 5 píxeles para velocidad)
        colores = []
        for y in range(0, imagen.height(), 5):
            for x in range(0, imagen.width(), 5):
                pixel = imagen.pixel(x, y)
                color = QColor(pixel)
                # Ignorar colores muy claros o muy oscuros (probablemente no son dominantes)
                if 30 < color.lightness() < 225:
                    colores.append((color.red(), color.green(), color.blue()))
        
        if not colores:
            return None
        
        # Encontrar colores más frecuentes
        contador = Counter(colores)
        colores_dominantes = contador.most_common(num_colores)
        
        # Convertir a lista de tuplas RGB
        return [color[0] for color in colores_dominantes]
    except Exception as e:
        print(f"Error al analizar imagen: {e}")
        return None


def generar_paleta_colores(colores_dominantes):
    """Genera una paleta de colores para las casillas basada en colores dominantes"""
    if not colores_dominantes or len(colores_dominantes) == 0:
        # Colores por defecto si no se pueden detectar
        return {
            "fondo": (100, 150, 200, 140),
            "borde": (50, 100, 150, 220),
            "boton_expandir": (70, 110, 150, 200),
            "texto": (255, 255, 255, 255),
            "lista_fondo": (60, 100, 140, 120),
            "lista_borde": (80, 120, 160, 180)
        }
    
    # Usar el color más dominante como base
    color_base = colores_dominantes[0]
    r_base, g_base, b_base = color_base
    
    # Calcular luminosidad para determinar si usar texto claro u oscuro
    luminosidad = (r_base * 0.299 + g_base * 0.587 + b_base * 0.114)
    
    # Ajustar el color base para mejor visibilidad
    # Si es muy oscuro, aclararlo un poco; si es muy claro, oscurecerlo un poco
    if luminosidad < 50:
        # Muy oscuro, aclarar un poco
        r_base = min(255, int(r_base * 1.3))
        g_base = min(255, int(g_base * 1.3))
        b_base = min(255, int(b_base * 1.3))
    elif luminosidad > 200:
        # Muy claro, oscurecer un poco
        r_base = max(0, int(r_base * 0.7))
        g_base = max(0, int(g_base * 0.7))
        b_base = max(0, int(b_base * 0.7))
    
    # Recalcular luminosidad después del ajuste
    luminosidad = (r_base * 0.299 + g_base * 0.587 + b_base * 0.114)
    
    # Generar colores de la paleta con mejor contraste
    # Fondo: color base con transparencia media (ajustada según luminosidad)
    if luminosidad < 100:
        # Fondo oscuro, usar más transparencia
        a_fondo = 160
    elif luminosidad > 180:
        # Fondo claro, usar menos transparencia para mejor visibilidad
        a_fondo = 180
    else:
        a_fondo = 140
    fondo = (r_base, g_base, b_base, a_fondo)
    
    # Borde: color base más oscuro pero con buen contraste
    r_borde = max(0, min(255, int(r_base * 0.65)))
    g_borde = max(0, min(255, int(g_base * 0.65)))
    b_borde = max(0, min(255, int(b_base * 0.65)))
    borde = (r_borde, g_borde, b_borde, 220)
    
    # Botón: color base ligeramente más oscuro
    r_boton = max(0, min(255, int(r_base * 0.75)))
    g_boton = max(0, min(255, int(g_base * 0.75)))
    b_boton = max(0, min(255, int(b_base * 0.75)))
    boton_expandir = (r_boton, g_boton, b_boton, 200)
    
    # Texto: blanco si el fondo es oscuro, negro si es claro
    if luminosidad < 120:
        texto = (255, 255, 255, 255)
    else:
        texto = (30, 30, 30, 255)
    
    # Lista fondo: color base más oscuro y transparente
    r_lista = max(0, min(255, int(r_base * 0.55)))
    g_lista = max(0, min(255, int(g_base * 0.55)))
    b_lista = max(0, min(255, int(b_base * 0.55)))
    lista_fondo = (r_lista, g_lista, b_lista, 120)
    
    # Lista borde: color base medio
    r_lista_borde = max(0, min(255, int(r_base * 0.7)))
    g_lista_borde = max(0, min(255, int(g_base * 0.7)))
    b_lista_borde = max(0, min(255, int(b_base * 0.7)))
    lista_borde = (r_lista_borde, g_lista_borde, b_lista_borde, 180)
    
    return {
        "fondo": fondo,
        "borde": borde,
        "boton_expandir": boton_expandir,
        "texto": texto,
        "lista_fondo": lista_fondo,
        "lista_borde": lista_borde
    }


class DialogConfigurarColores(QDialog):
    """Diálogo para configurar los colores de las casillas"""
    
    def __init__(self, parent=None, colores_actuales=None):
        super().__init__(parent)
        self.colores_seleccionados = {}
        self.colores_actuales = colores_actuales or {}
        self.setup_ui()
        self.cargar_colores_actuales()
        
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Configurar Colores")
        self.setFixedSize(450, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        titulo = QLabel("Personaliza los colores de las casillas:")
        titulo.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(titulo)
        
        # Grupo de colores
        grupo = QGroupBox("Colores")
        grupo_layout = QGridLayout()
        grupo_layout.setSpacing(10)
        
        # Color de fondo
        self.crear_selector_color(grupo_layout, "Fondo de la casilla:", "fondo", 0, 
                                 (100, 150, 200, 140))
        
        # Color del borde
        self.crear_selector_color(grupo_layout, "Borde:", "borde", 1,
                                 (50, 100, 150, 220))
        
        # Color del botón expandir
        self.crear_selector_color(grupo_layout, "Botón expandir:", "boton_expandir", 2,
                                 (70, 110, 150, 200))
        
        # Color del texto
        self.crear_selector_color(grupo_layout, "Texto:", "texto", 3,
                                 (255, 255, 255, 255))
        
        # Color de la lista de archivos
        self.crear_selector_color(grupo_layout, "Fondo lista archivos:", "lista_fondo", 4,
                                 (60, 100, 140, 120))
        
        # Color del borde de la lista
        self.crear_selector_color(grupo_layout, "Borde lista:", "lista_borde", 5,
                                 (80, 120, 160, 180))
        
        grupo.setLayout(grupo_layout)
        layout.addWidget(grupo)
        
        # Botón para detectar automáticamente
        btn_detectar = QPushButton("🎨 Detectar Colores del Fondo Automáticamente")
        btn_detectar.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 130, 180, 200);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(90, 150, 200, 220);
            }
        """)
        btn_detectar.clicked.connect(self.detectar_colores_automatico)
        layout.addWidget(btn_detectar)
        
        layout.addStretch()
        
        # Botones
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.aceptar)
        botones.rejected.connect(self.reject)
        
        botones.button(QDialogButtonBox.Ok).setText("Aplicar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        
        layout.addWidget(botones)
        
        self.setLayout(layout)
        
    def crear_selector_color(self, layout, etiqueta, clave, fila, color_default):
        """Crea un selector de color con etiqueta y botón"""
        label = QLabel(etiqueta)
        label.setStyleSheet("font-size: 11px;")
        
        # Botón que muestra el color actual
        btn_color = QPushButton()
        btn_color.setFixedSize(60, 30)
        btn_color.setObjectName(f"btn_{clave}")
        
        # Obtener color actual o usar el default
        color_actual = self.colores_actuales.get(clave, color_default)
        if isinstance(color_actual, (list, tuple)) and len(color_actual) == 4:
            r, g, b, a = color_actual
        elif isinstance(color_actual, (list, tuple)) and len(color_actual) == 3:
            r, g, b = color_actual
            a = 255
        else:
            r, g, b, a = color_default
        
        self.colores_seleccionados[clave] = (r, g, b, a)
        
        # Establecer color del botón
        btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, {a});
                border: 1px solid rgba(150, 150, 150, 200);
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(200, 200, 200, 255);
            }}
        """)
        
        # Conectar al selector de color
        btn_color.clicked.connect(lambda checked, c=clave: self.seleccionar_color(c))
        
        layout.addWidget(label, fila, 0)
        layout.addWidget(btn_color, fila, 1)
        
    def seleccionar_color(self, clave):
        """Abre el selector de color y actualiza el botón"""
        color_actual = self.colores_seleccionados.get(clave, (255, 255, 255, 255))
        r, g, b, a = color_actual
        
        # QColorDialog usa RGB sin alpha en algunos casos, pero podemos manejarlo
        color_qcolor = QColor(r, g, b, a)
        color_seleccionado = QColorDialog.getColor(color_qcolor, self, f"Seleccionar color para {clave}")
        
        if color_seleccionado.isValid():
            r = color_seleccionado.red()
            g = color_seleccionado.green()
            b = color_seleccionado.blue()
            a = color_seleccionado.alpha()
            
            self.colores_seleccionados[clave] = (r, g, b, a)
            
            # Actualizar el botón
            btn = self.findChild(QPushButton, f"btn_{clave}")
            if btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba({r}, {g}, {b}, {a});
                        border: 1px solid rgba(150, 150, 150, 200);
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid rgba(200, 200, 200, 255);
                    }}
                """)
    
    def detectar_colores_automatico(self):
        """Detecta automáticamente los colores del fondo de escritorio"""
        # Obtener ruta del fondo
        ruta_fondo = obtener_ruta_fondo_escritorio()
        
        if not ruta_fondo:
            QMessageBox.warning(
                self, 
                "No se pudo detectar", 
                "No se pudo obtener la ruta del fondo de escritorio.\n"
                "Asegúrate de tener un fondo de escritorio configurado."
            )
            return
        
        # Analizar colores
        colores_dominantes = analizar_colores_imagen(ruta_fondo)
        
        if not colores_dominantes:
            QMessageBox.warning(
                self,
                "No se pudieron analizar colores",
                "No se pudieron extraer colores del fondo de escritorio.\n"
                "Intenta con otro fondo de escritorio."
            )
            return
        
        # Generar paleta
        paleta = generar_paleta_colores(colores_dominantes)
        
        # Actualizar colores seleccionados
        self.colores_seleccionados = paleta.copy()
        
        # Actualizar todos los botones de color
        for clave, color in paleta.items():
            r, g, b, a = color
            btn = self.findChild(QPushButton, f"btn_{clave}")
            if btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba({r}, {g}, {b}, {a});
                        border: 1px solid rgba(150, 150, 150, 200);
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid rgba(200, 200, 200, 255);
                    }}
                """)
        
        QMessageBox.information(
            self,
            "Colores detectados",
            f"Se detectaron colores del fondo de escritorio:\n{ruta_fondo}\n\n"
            "Los colores se han aplicado. Haz clic en 'Aplicar' para guardarlos."
        )
    
    def cargar_colores_actuales(self):
        """Carga los colores actuales si existen"""
        if self.colores_actuales:
            for clave, color in self.colores_actuales.items():
                if clave in self.colores_seleccionados:
                    self.colores_seleccionados[clave] = color
                    # Actualizar botón
                    btn = self.findChild(QPushButton, f"btn_{clave}")
                    if btn:
                        r, g, b, a = color
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba({r}, {g}, {b}, {a});
                                border: 1px solid rgba(150, 150, 150, 200);
                                border-radius: 4px;
                            }}
                            QPushButton:hover {{
                                border: 2px solid rgba(200, 200, 200, 255);
                            }}
                        """)
    
    def aceptar(self):
        """Acepta el diálogo y guarda los colores"""
        self.accept()


class DialogConfiguracionesAvanzadas(QDialog):
    """Diálogo de configuraciones avanzadas con todas las opciones"""
    
    def __init__(self, parent, parent_app):
        super().__init__(parent)
        self.parent_app = parent_app
        self.setup_ui()
        self.cargar_configuraciones()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("⚙️ Configuraciones Avanzadas")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        
        # Crear pestañas
        tabs = QTabWidget()
        
        # Pestaña 1: Colores
        tab_colores = QWidget()
        layout_colores = QVBoxLayout()
        layout_colores.setSpacing(10)
        
        # Botón para abrir el diálogo de colores completo
        btn_colores = QPushButton("🎨 Configurar Colores")
        btn_colores.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 150, 200, 200);
                color: white;
                border: 1px solid rgba(80, 120, 160, 220);
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 170, 220, 240);
            }
        """)
        btn_colores.clicked.connect(self.abrir_dialogo_colores)
        
        label_info_colores = QLabel(
            "Haz clic en el botón para abrir el diálogo completo de configuración de colores.\n"
            "Puedes personalizar todos los colores de las casillas y detectar colores automáticamente del fondo de escritorio."
        )
        label_info_colores.setWordWrap(True)
        label_info_colores.setStyleSheet("color: #666; font-size: 10px;")
        
        layout_colores.addWidget(btn_colores)
        layout_colores.addWidget(label_info_colores)
        layout_colores.addStretch()
        tab_colores.setLayout(layout_colores)
        
        # Pestaña 2: Tamaños
        tab_tamanos = QWidget()
        layout_tamanos = QVBoxLayout()
        layout_tamanos.setSpacing(15)
        
        # Tamaño de iconos por defecto
        grupo_iconos = QGroupBox("Tamaño de Iconos por Defecto")
        grupo_iconos.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(100, 150, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_iconos = QVBoxLayout()
        layout_iconos.setSpacing(10)
        
        label_iconos = QLabel("Tamaño de iconos para nuevas casillas (16-64 píxeles):")
        self.spin_iconos = QSpinBox()
        self.spin_iconos.setRange(16, 64)
        self.spin_iconos.setValue(24)
        self.spin_iconos.setSuffix(" px")
        self.spin_iconos.valueChanged.connect(self.actualizar_porcentaje_iconos)
        
        # Label para mostrar porcentaje
        self.label_porcentaje_iconos = QLabel("Porcentaje: 16.7%")
        self.label_porcentaje_iconos.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        
        # Slider para tamaño de iconos
        self.slider_iconos = QSlider(Qt.Horizontal)
        self.slider_iconos.setRange(16, 64)
        self.slider_iconos.setValue(24)
        self.slider_iconos.valueChanged.connect(self.spin_iconos.setValue)
        self.spin_iconos.valueChanged.connect(self.slider_iconos.setValue)
        self.spin_iconos.valueChanged.connect(self.actualizar_porcentaje_iconos)
        
        layout_iconos.addWidget(label_iconos)
        layout_iconos.addWidget(self.spin_iconos)
        layout_iconos.addWidget(self.label_porcentaje_iconos)
        layout_iconos.addWidget(self.slider_iconos)
        grupo_iconos.setLayout(layout_iconos)
        
        # Resolución de iconos (calidad)
        grupo_resolucion = QGroupBox("Resolución de Iconos (Calidad)")
        grupo_resolucion.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(100, 150, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_resolucion = QVBoxLayout()
        layout_resolucion.setSpacing(10)
        
        label_resolucion = QLabel(
            "Multiplicador de resolución (1.0x = calidad normal, 2.0x = alta calidad, 3.0x = máxima calidad):\n"
            "Valores más altos mejoran la calidad pero usan más memoria."
        )
        label_resolucion.setWordWrap(True)
        label_resolucion.setStyleSheet("color: #666; font-size: 10px;")
        
        layout_controles_resolucion = QHBoxLayout()
        layout_controles_resolucion.setSpacing(10)
        
        self.spin_resolucion = QDoubleSpinBox()
        self.spin_resolucion.setRange(1.0, 5.0)
        self.spin_resolucion.setValue(2.0)  # 2.0x por defecto
        self.spin_resolucion.setSuffix("x")
        self.spin_resolucion.setSingleStep(0.1)  # Incrementos de 0.1x
        self.spin_resolucion.setDecimals(1)
        self.spin_resolucion.valueChanged.connect(self.actualizar_label_resolucion)
        
        # Slider para resolución (10 = 1.0x, 20 = 2.0x, 30 = 3.0x, etc.)
        self.slider_resolucion = QSlider(Qt.Horizontal)
        self.slider_resolucion.setRange(10, 50)  # 1.0x a 5.0x (multiplicado por 10)
        self.slider_resolucion.setValue(20)  # 2.0x por defecto
        self.slider_resolucion.setSingleStep(1)
        # Conectar slider a spinbox (convertir 10-50 a 1.0-5.0)
        self.slider_resolucion.valueChanged.connect(
            lambda v: self.spin_resolucion.setValue(v / 10.0)
        )
        self.spin_resolucion.valueChanged.connect(
            lambda v: self.slider_resolucion.setValue(int(v * 10))
        )
        self.spin_resolucion.valueChanged.connect(self.actualizar_label_resolucion)
        
        # Label para mostrar el valor real (1.0x, 2.0x, etc.)
        self.label_resolucion_valor = QLabel("Resolución: 2.0x")
        self.label_resolucion_valor.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        
        layout_controles_resolucion.addWidget(QLabel("Multiplicador:"))
        layout_controles_resolucion.addWidget(self.spin_resolucion)
        layout_controles_resolucion.addWidget(self.label_resolucion_valor)
        layout_controles_resolucion.addStretch()
        
        layout_resolucion.addWidget(label_resolucion)
        layout_resolucion.addLayout(layout_controles_resolucion)
        layout_resolucion.addWidget(self.slider_resolucion)
        grupo_resolucion.setLayout(layout_resolucion)
        
        # Tamaños de casillas por defecto
        grupo_casillas = QGroupBox("Tamaños de Casillas por Defecto")
        grupo_casillas.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(100, 150, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_casillas = QGridLayout()
        layout_casillas.setSpacing(10)
        
        # Tamaño colapsado
        label_colapsado = QLabel("Tamaño Colapsado:")
        self.spin_colapsado_ancho = QSpinBox()
        self.spin_colapsado_ancho.setRange(100, 800)
        self.spin_colapsado_ancho.setSuffix(" px")
        self.spin_colapsado_alto = QSpinBox()
        self.spin_colapsado_alto.setRange(40, 600)
        self.spin_colapsado_alto.setSuffix(" px")
        
        # Tamaño expandido
        label_expandido = QLabel("Tamaño Expandido:")
        self.spin_expandido_ancho = QSpinBox()
        self.spin_expandido_ancho.setRange(100, 800)
        self.spin_expandido_ancho.setSuffix(" px")
        self.spin_expandido_alto = QSpinBox()
        self.spin_expandido_alto.setRange(40, 600)
        self.spin_expandido_alto.setSuffix(" px")
        
        layout_casillas.addWidget(label_colapsado, 0, 0)
        layout_casillas.addWidget(QLabel("Ancho:"), 0, 1)
        layout_casillas.addWidget(self.spin_colapsado_ancho, 0, 2)
        layout_casillas.addWidget(QLabel("Alto:"), 0, 3)
        layout_casillas.addWidget(self.spin_colapsado_alto, 0, 4)
        
        layout_casillas.addWidget(label_expandido, 1, 0)
        layout_casillas.addWidget(QLabel("Ancho:"), 1, 1)
        layout_casillas.addWidget(self.spin_expandido_ancho, 1, 2)
        layout_casillas.addWidget(QLabel("Alto:"), 1, 3)
        layout_casillas.addWidget(self.spin_expandido_alto, 1, 4)
        
        grupo_casillas.setLayout(layout_casillas)
        
        # Tamaño General (aplicar a todas las casillas)
        grupo_general = QGroupBox("Tamaño General - Aplicar a Todas las Casillas")
        grupo_general.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(150, 100, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_general = QVBoxLayout()
        layout_general.setSpacing(10)
        
        label_info_general = QLabel(
            "Ajusta el tamaño de iconos para TODAS las casillas existentes de una vez.\n"
            "Esto sobrescribirá los tamaños individuales de cada casilla."
        )
        label_info_general.setWordWrap(True)
        label_info_general.setStyleSheet("color: #666; font-size: 10px;")
        
        # Controles para tamaño general
        layout_controles_general = QHBoxLayout()
        layout_controles_general.setSpacing(10)
        
        label_general = QLabel("Tamaño de iconos:")
        self.spin_iconos_general = QSpinBox()
        self.spin_iconos_general.setRange(16, 64)
        self.spin_iconos_general.setValue(24)
        self.spin_iconos_general.setSuffix(" px")
        
        # Label para porcentaje general
        self.label_porcentaje_general = QLabel("Porcentaje: 16.7%")
        self.label_porcentaje_general.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        
        # Slider para tamaño general
        self.slider_iconos_general = QSlider(Qt.Horizontal)
        self.slider_iconos_general.setRange(16, 64)
        self.slider_iconos_general.setValue(24)
        self.slider_iconos_general.valueChanged.connect(self.spin_iconos_general.setValue)
        self.spin_iconos_general.valueChanged.connect(self.slider_iconos_general.setValue)
        self.spin_iconos_general.valueChanged.connect(self.actualizar_porcentaje_general)
        
        layout_controles_general.addWidget(label_general)
        layout_controles_general.addWidget(self.spin_iconos_general)
        layout_controles_general.addWidget(self.label_porcentaje_general)
        layout_controles_general.addStretch()
        
        # Botón para aplicar a todas
        btn_aplicar_todas = QPushButton("Aplicar a Todas las Casillas")
        btn_aplicar_todas.setStyleSheet("""
            QPushButton {
                background-color: rgba(150, 100, 200, 200);
                color: white;
                border: 1px solid rgba(120, 80, 170, 220);
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(170, 120, 220, 240);
            }
        """)
        btn_aplicar_todas.clicked.connect(self.aplicar_tamano_todas_casillas)
        
        layout_general.addWidget(label_info_general)
        layout_general.addLayout(layout_controles_general)
        layout_general.addWidget(self.slider_iconos_general)
        layout_general.addWidget(btn_aplicar_todas)
        grupo_general.setLayout(layout_general)
        
        layout_tamanos.addWidget(grupo_iconos)
        layout_tamanos.addWidget(grupo_resolucion)
        layout_tamanos.addWidget(grupo_casillas)
        layout_tamanos.addWidget(grupo_general)
        layout_tamanos.addStretch()
        tab_tamanos.setLayout(layout_tamanos)
        
        # Pestaña 3: Desplazamiento (Scroll)
        tab_scroll = QWidget()
        layout_scroll = QVBoxLayout()
        layout_scroll.setSpacing(15)
        
        # Velocidad de desplazamiento
        grupo_velocidad_scroll = QGroupBox("Velocidad de Desplazamiento")
        grupo_velocidad_scroll.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(100, 150, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_velocidad_scroll = QVBoxLayout()
        layout_velocidad_scroll.setSpacing(10)
        
        label_velocidad_scroll = QLabel(
            "Ajusta qué tan rápido quieres que se desplace el contenido cuando uses la rueda del mouse.\n"
            "100% = velocidad normal, valores más altos = más rápido, valores más bajos = más lento."
        )
        label_velocidad_scroll.setWordWrap(True)
        label_velocidad_scroll.setStyleSheet("color: #666; font-size: 10px;")
        
        layout_controles_scroll = QHBoxLayout()
        layout_controles_scroll.setSpacing(10)
        
        self.spin_velocidad_scroll = QSpinBox()
        self.spin_velocidad_scroll.setRange(10, 500)  # 10% a 500%
        self.spin_velocidad_scroll.setValue(100)  # 100% por defecto
        self.spin_velocidad_scroll.setSuffix("%")
        self.spin_velocidad_scroll.setSingleStep(10)
        self.spin_velocidad_scroll.valueChanged.connect(self.actualizar_label_velocidad_scroll)
        
        # Slider para velocidad de scroll
        self.slider_velocidad_scroll = QSlider(Qt.Horizontal)
        self.slider_velocidad_scroll.setRange(10, 500)  # 10% a 500%
        self.slider_velocidad_scroll.setValue(100)  # 100% por defecto
        self.slider_velocidad_scroll.setSingleStep(10)
        self.slider_velocidad_scroll.valueChanged.connect(self.spin_velocidad_scroll.setValue)
        self.spin_velocidad_scroll.valueChanged.connect(self.slider_velocidad_scroll.setValue)
        self.spin_velocidad_scroll.valueChanged.connect(self.actualizar_label_velocidad_scroll)
        
        # Label para mostrar descripción de la velocidad
        self.label_descripcion_scroll = QLabel("Velocidad: Normal (100%)")
        self.label_descripcion_scroll.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        
        layout_controles_scroll.addWidget(QLabel("Velocidad:"))
        layout_controles_scroll.addWidget(self.spin_velocidad_scroll)
        layout_controles_scroll.addWidget(self.label_descripcion_scroll)
        layout_controles_scroll.addStretch()
        
        layout_velocidad_scroll.addWidget(label_velocidad_scroll)
        layout_velocidad_scroll.addLayout(layout_controles_scroll)
        layout_velocidad_scroll.addWidget(self.slider_velocidad_scroll)
        grupo_velocidad_scroll.setLayout(layout_velocidad_scroll)
        
        layout_scroll.addWidget(grupo_velocidad_scroll)
        layout_scroll.addStretch()
        tab_scroll.setLayout(layout_scroll)
        
        # Agregar pestañas
        # Pestaña 4: Vistas
        tab_vistas = QWidget()
        layout_vistas = QVBoxLayout()
        layout_vistas.setSpacing(15)
        
        # Tipo de vista por defecto
        grupo_vista_defecto = QGroupBox("Tipo de Vista por Defecto")
        grupo_vista_defecto.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(100, 150, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_vista_defecto = QVBoxLayout()
        layout_vista_defecto.setSpacing(10)
        
        label_vista_defecto = QLabel("Selecciona el tipo de vista por defecto para nuevas casillas:")
        label_vista_defecto.setWordWrap(True)
        label_vista_defecto.setStyleSheet("color: #666; font-size: 10px;")
        
        self.radio_lista_defecto = QRadioButton("Vista de Lista")
        self.radio_cuadricula_defecto = QRadioButton("Vista de Cuadrícula")
        self.radio_lista_defecto.setChecked(True)  # Por defecto lista
        
        grupo_radio_vista = QButtonGroup()
        grupo_radio_vista.addButton(self.radio_lista_defecto)
        grupo_radio_vista.addButton(self.radio_cuadricula_defecto)
        
        layout_vista_defecto.addWidget(label_vista_defecto)
        layout_vista_defecto.addWidget(self.radio_lista_defecto)
        layout_vista_defecto.addWidget(self.radio_cuadricula_defecto)
        grupo_vista_defecto.setLayout(layout_vista_defecto)
        
        # Aplicar vista a todas las casillas
        grupo_vista_general = QGroupBox("Vista General - Aplicar a Todas las Casillas")
        grupo_vista_general.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(150, 100, 200, 180);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        layout_vista_general = QVBoxLayout()
        layout_vista_general.setSpacing(10)
        
        label_info_vista_general = QLabel(
            "Aplica el tipo de vista a TODAS las casillas existentes de una vez.\n"
            "Esto sobrescribirá los tipos de vista individuales de cada casilla."
        )
        label_info_vista_general.setWordWrap(True)
        label_info_vista_general.setStyleSheet("color: #666; font-size: 10px;")
        
        layout_radio_general = QVBoxLayout()
        self.radio_lista_general = QRadioButton("Vista de Lista")
        self.radio_cuadricula_general = QRadioButton("Vista de Cuadrícula")
        self.radio_lista_general.setChecked(True)
        
        grupo_radio_vista_general = QButtonGroup()
        grupo_radio_vista_general.addButton(self.radio_lista_general)
        grupo_radio_vista_general.addButton(self.radio_cuadricula_general)
        
        layout_radio_general.addWidget(self.radio_lista_general)
        layout_radio_general.addWidget(self.radio_cuadricula_general)
        
        btn_aplicar_vista_todas = QPushButton("Aplicar Vista a Todas las Casillas")
        btn_aplicar_vista_todas.clicked.connect(self.aplicar_vista_todas_casillas)
        btn_aplicar_vista_todas.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 150, 200, 200);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 170, 220, 220);
            }
        """)
        
        layout_vista_general.addWidget(label_info_vista_general)
        layout_vista_general.addLayout(layout_radio_general)
        layout_vista_general.addWidget(btn_aplicar_vista_todas)
        grupo_vista_general.setLayout(layout_vista_general)
        
        layout_vistas.addWidget(grupo_vista_defecto)
        layout_vistas.addWidget(grupo_vista_general)
        layout_vistas.addStretch()
        tab_vistas.setLayout(layout_vistas)
        
        tabs.addTab(tab_colores, "🎨 Colores")
        tabs.addTab(tab_tamanos, "📏 Tamaños")
        tabs.addTab(tab_scroll, "🖱️ Desplazamiento")
        tabs.addTab(tab_vistas, "👁️ Vistas")
        
        layout_principal.addWidget(tabs)
        
        # Botones
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.aceptar)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)
        
        self.setLayout(layout_principal)
    
    def calcular_porcentaje_iconos(self, tamano):
        """Calcula el porcentaje del tamaño de iconos (16px = 0%, 64px = 100%)"""
        rango_min = 16
        rango_max = 64
        rango_total = rango_max - rango_min
        porcentaje = ((tamano - rango_min) / rango_total) * 100
        return round(porcentaje, 1)
    
    def actualizar_porcentaje_iconos(self, valor):
        """Actualiza el label de porcentaje para iconos por defecto"""
        porcentaje = self.calcular_porcentaje_iconos(valor)
        self.label_porcentaje_iconos.setText(f"Porcentaje: {porcentaje}%")
    
    def actualizar_porcentaje_general(self, valor):
        """Actualiza el label de porcentaje para tamaño general"""
        porcentaje = self.calcular_porcentaje_iconos(valor)
        self.label_porcentaje_general.setText(f"Porcentaje: {porcentaje}%")
    
    def actualizar_label_resolucion(self, valor):
        """Actualiza el label de resolución"""
        self.label_resolucion_valor.setText(f"Resolución: {valor:.1f}x")
    
    def actualizar_label_velocidad_scroll(self, valor):
        """Actualiza el label de descripción de velocidad de scroll"""
        if valor < 50:
            descripcion = "Muy lento"
        elif valor < 80:
            descripcion = "Lento"
        elif valor < 120:
            descripcion = "Normal"
        elif valor < 200:
            descripcion = "Rápido"
        elif valor < 300:
            descripcion = "Muy rápido"
        else:
            descripcion = "Extremadamente rápido"
        
        self.label_descripcion_scroll.setText(f"Velocidad: {descripcion} ({valor}%)")
    
    def aplicar_tamano_todas_casillas(self):
        """Aplica el tamaño de iconos a todas las casillas existentes"""
        tamano = self.spin_iconos_general.value()
        porcentaje = self.calcular_porcentaje_iconos(tamano)
        
        respuesta = QMessageBox.question(
            self,
            "Aplicar a Todas las Casillas",
            f"¿Estás seguro de que quieres cambiar el tamaño de iconos a {tamano}px ({porcentaje}%) "
            f"en TODAS las {len(self.parent_app.casillas)} casillas existentes?\n\n"
            "Esto sobrescribirá los tamaños individuales de cada casilla.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            # Aplicar a todas las casillas
            for nombre, casilla in self.parent_app.casillas.items():
                casilla.tamano_iconos = tamano
                casilla.actualizar_tamano_iconos()
                # Procesar eventos para asegurar que la UI se actualice
                QApplication.processEvents()
                # Actualizar la lista de archivos para aplicar el nuevo tamaño de iconos
                casilla.actualizar_lista_archivos()
                # Guardar el tamaño para cada casilla
                self.parent_app.guardar_tamano_iconos(nombre, tamano)
            
            # Guardar todas las posiciones una vez más para asegurar que todo esté guardado
            self.parent_app.guardar_posiciones()
            
            QMessageBox.information(
                self,
                "Tamaño Aplicado",
                f"Se ha aplicado el tamaño de {tamano}px ({porcentaje}%) a todas las casillas."
            )
    
    def aplicar_vista_todas_casillas(self):
        """Aplica el tipo de vista a todas las casillas existentes"""
        tipo_vista = "lista" if self.radio_lista_general.isChecked() else "cuadricula"
        
        respuesta = QMessageBox.question(
            self,
            "Aplicar Vista a Todas las Casillas",
            f"¿Estás seguro de que quieres cambiar el tipo de vista a '{'Lista' if tipo_vista == 'lista' else 'Cuadrícula'}' "
            f"en TODAS las {len(self.parent_app.casillas)} casillas existentes?\n\n"
            "Esto sobrescribirá los tipos de vista individuales de cada casilla.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            # Aplicar a todas las casillas
            for nombre, casilla in self.parent_app.casillas.items():
                casilla.tipo_vista = tipo_vista
                casilla.aplicar_tipo_vista()
                casilla.actualizar_lista_archivos()
                # Guardar el tipo de vista para cada casilla
                self.parent_app.guardar_tipo_vista(nombre, tipo_vista)
            
            QMessageBox.information(
                self,
                "Vista Aplicada",
                f"Se ha aplicado la vista de {'Lista' if tipo_vista == 'lista' else 'Cuadrícula'} a todas las casillas."
            )
    
    def abrir_dialogo_colores(self):
        """Abre el diálogo completo de colores"""
        colores_actuales = self.parent_app.obtener_colores_guardados()
        dialog = DialogConfigurarColores(self, colores_actuales)
        if dialog.exec_() == QDialog.Accepted:
            self.parent_app.aplicar_colores(dialog.colores_seleccionados)
    
    def cargar_configuraciones(self):
        """Carga las configuraciones guardadas"""
        # Cargar tamaño de iconos por defecto
        if "configuraciones" in self.parent_app.posiciones:
            config = self.parent_app.posiciones["configuraciones"]
            if "tamano_iconos_defecto" in config:
                self.spin_iconos.setValue(config["tamano_iconos_defecto"])
            else:
                # Usar valor por defecto de 24
                self.spin_iconos.setValue(24)
            
            if "tamano_colapsado_defecto" in config:
                ancho, alto = config["tamano_colapsado_defecto"]
                self.spin_colapsado_ancho.setValue(ancho)
                self.spin_colapsado_alto.setValue(alto)
            else:
                # Usar valores por defecto
                self.spin_colapsado_ancho.setValue(140)
                self.spin_colapsado_alto.setValue(50)
            
            if "tamano_expandido_defecto" in config:
                ancho, alto = config["tamano_expandido_defecto"]
                self.spin_expandido_ancho.setValue(ancho)
                self.spin_expandido_alto.setValue(alto)
            else:
                # Usar valores por defecto
                self.spin_expandido_ancho.setValue(280)
                self.spin_expandido_alto.setValue(400)
            
            # Cargar multiplicador de resolución de iconos
            if "multiplicador_resolucion_iconos" in config:
                multiplicador = config["multiplicador_resolucion_iconos"]
                self.spin_resolucion.setValue(multiplicador)
            else:
                # Usar valor por defecto de 2.0x
                self.spin_resolucion.setValue(2.0)
            
            # Cargar tipo de vista por defecto
            if "tipo_vista_defecto" in config:
                tipo_vista = config["tipo_vista_defecto"]
                if tipo_vista == "cuadricula":
                    self.radio_cuadricula_defecto.setChecked(True)
                else:
                    self.radio_lista_defecto.setChecked(True)
            else:
                # Por defecto lista
                self.radio_lista_defecto.setChecked(True)
            
            # Cargar velocidad de scroll
            if "velocidad_scroll" in config:
                velocidad = config["velocidad_scroll"]
                self.spin_velocidad_scroll.setValue(int(velocidad))
            else:
                # Por defecto 100%
                self.spin_velocidad_scroll.setValue(100)
        else:
            # Valores por defecto si no hay configuraciones
            self.spin_iconos.setValue(24)
            self.spin_colapsado_ancho.setValue(140)
            self.spin_colapsado_alto.setValue(50)
            self.spin_expandido_ancho.setValue(280)
            self.spin_expandido_alto.setValue(400)
            self.spin_resolucion.setValue(2.0)  # 2.0x por defecto
            self.radio_lista_defecto.setChecked(True)  # Por defecto lista
            self.spin_velocidad_scroll.setValue(100)  # 100% por defecto
        
        # Inicializar el tamaño general con el valor por defecto
        self.spin_iconos_general.setValue(self.spin_iconos.value())
        
        # Actualizar porcentajes iniciales
        self.actualizar_porcentaje_iconos(self.spin_iconos.value())
        self.actualizar_porcentaje_general(self.spin_iconos_general.value())
        self.actualizar_label_resolucion(self.spin_resolucion.value())
        self.actualizar_label_velocidad_scroll(self.spin_velocidad_scroll.value())
    
    def aceptar(self):
        """Guarda las configuraciones"""
        # Guardar configuraciones
        if "configuraciones" not in self.parent_app.posiciones:
            self.parent_app.posiciones["configuraciones"] = {}
        
        config = self.parent_app.posiciones["configuraciones"]
        config["tamano_iconos_defecto"] = self.spin_iconos.value()
        config["tamano_colapsado_defecto"] = (
            self.spin_colapsado_ancho.value(),
            self.spin_colapsado_alto.value()
        )
        config["tamano_expandido_defecto"] = (
            self.spin_expandido_ancho.value(),
            self.spin_expandido_alto.value()
        )
        # Guardar multiplicador de resolución
        config["multiplicador_resolucion_iconos"] = self.spin_resolucion.value()
        
        # Guardar tipo de vista por defecto
        tipo_vista_defecto = "cuadricula" if self.radio_cuadricula_defecto.isChecked() else "lista"
        config["tipo_vista_defecto"] = tipo_vista_defecto
        
        # Guardar velocidad de scroll
        config["velocidad_scroll"] = float(self.spin_velocidad_scroll.value())
        
        self.parent_app.guardar_posiciones()
        
        # Aplicar tamaño de iconos, resolución y velocidad de scroll por defecto a todas las casillas existentes
        tamano_iconos = self.spin_iconos.value()
        multiplicador_resolucion = self.spin_resolucion.value()
        velocidad_scroll = float(self.spin_velocidad_scroll.value())
        for nombre, casilla in self.parent_app.casillas.items():
            casilla.tamano_iconos = tamano_iconos
            casilla.multiplicador_resolucion_iconos = multiplicador_resolucion
            casilla.velocidad_scroll = velocidad_scroll
            casilla.actualizar_tamano_iconos()
            casilla.actualizar_velocidad_scroll()
            casilla.actualizar_lista_archivos()
        
        QMessageBox.information(
            self,
            "Configuraciones Guardadas",
            "Las configuraciones se han guardado correctamente.\n\n"
            "Nota: Los tamaños de casillas por defecto se aplicarán a las nuevas casillas que crees."
        )
        self.accept()


class VentanaResultadosBusqueda(QWidget):
    """Ventana que muestra los resultados de búsqueda"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz de resultados"""
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 300)
        
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 50, 50, 220);
                border: 2px solid rgba(100, 100, 100, 220);
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        titulo = QLabel("Resultados de búsqueda")
        titulo.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        
        self.lista_resultados = QListWidget()
        self.lista_resultados.setStyleSheet("""
            QListWidget {
                background-color: rgba(60, 60, 60, 200);
                border: 1px solid rgba(100, 100, 100, 200);
                border-radius: 4px;
                color: white;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(80, 80, 80, 150);
            }
            QListWidget::item:hover {
                background-color: rgba(80, 80, 80, 200);
            }
        """)
        self.lista_resultados.itemDoubleClicked.connect(self.abrir_resultado)
        
        layout.addWidget(titulo)
        layout.addWidget(self.lista_resultados)
        
        frame.setLayout(layout)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(frame)
        
        self.setLayout(main_layout)
        self.hide()
        
    def mostrar_resultados(self, resultados):
        """Muestra los resultados en la lista"""
        self.lista_resultados.clear()
        
        if not resultados:
            item = QListWidgetItem("No se encontraron resultados")
            item.setFlags(Qt.NoItemFlags)
            self.lista_resultados.addItem(item)
            return
        
        for r in resultados[:20]:  # Máximo 20 resultados
            tipo = "📁" if r['es_carpeta'] else "📄"
            texto = f"{tipo} {r['nombre']} (en: {r['casilla']})"
            item = QListWidgetItem(texto)
            item.setData(Qt.UserRole, r)
            self.lista_resultados.addItem(item)
        
    def abrir_resultado(self, item):
        """Abre el archivo o carpeta del resultado"""
        datos = item.data(Qt.UserRole)
        if datos:
            ruta = datos['ruta']
            try:
                elemento = Path(ruta)
                if elemento.exists():
                    os.startfile(str(elemento))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo abrir: {str(e)}")


class PanelControl(QWidget):
    """Panel de control compacto para crear nuevas casillas"""
    
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.ventana_resultados = VentanaResultadosBusqueda(self)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del panel de control"""
        # Hacer la ventana transparente y sin bordes
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Tamaño compacto
        self.setFixedSize(400, 70)
        
        # Posición inicial (esquina superior izquierda)
        screen = QApplication.primaryScreen().geometry()
        self.move(20, 20)
        
        # Frame principal
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 180);
                border: 1px solid rgba(100, 100, 100, 220);
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Campo de búsqueda
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar archivos...")
        self.input_buscar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(150, 150, 150, 200);
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }
        """)
        self.input_buscar.textChanged.connect(self.buscar_archivos)
        
        # Botón menú (3 puntos)
        btn_menu = QPushButton("⋯")
        btn_menu.setMaximumSize(35, 35)
        btn_menu.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 200);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 220);
            }
        """)
        
        # Menú desplegable
        menu = QMenu(self)
        accion_crear = menu.addAction("Crear Casilla")
        accion_crear.triggered.connect(self.mostrar_dialogo_crear)
        menu.addSeparator()
        accion_eliminar = menu.addAction("🗑️ Eliminar Casilla")
        accion_eliminar.triggered.connect(self.mostrar_dialogo_eliminar)
        menu.addSeparator()
        accion_colores = menu.addAction("Configurar Colores")
        accion_colores.triggered.connect(self.mostrar_dialogo_colores)
        menu.addSeparator()
        accion_avanzadas = menu.addAction("⚙️ Configuraciones Avanzadas")
        accion_avanzadas.triggered.connect(self.mostrar_configuraciones_avanzadas)
        btn_menu.setMenu(menu)
        
        layout.addWidget(self.input_buscar, stretch=1)
        layout.addWidget(btn_menu)
        
        frame.setLayout(layout)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(frame)
        
        self.setLayout(main_layout)
        
        # Permitir mover la ventana
        self.old_pos = None
        
    def mousePressEvent(self, event):
        """Permite mover la ventana arrastrando"""
        if event.button() == Qt.LeftButton:
            # Solo mover si no se hace clic en el botón de menú (últimos 50px a la derecha)
            if event.pos().x() < self.width() - 50:
                self.old_pos = event.globalPos()
            else:
                self.old_pos = None
                
    def mouseMoveEvent(self, event):
        """Mueve la ventana cuando se arrastra"""
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()
            # Guardar posición
            if self.parent_app:
                self.parent_app.guardar_posicion_panel(self.pos())
            
    def mouseReleaseEvent(self, event):
        """Libera la posición al soltar el mouse"""
        self.old_pos = None
        
    def mostrar_dialogo_crear(self):
        """Muestra el diálogo para crear una casilla"""
        dialog = DialogCrearCasilla(self)
        if dialog.exec_() == QDialog.Accepted:
            nombre = dialog.nombre_casilla
            if nombre:
                self.parent_app.crear_casilla(nombre)
    
    def mostrar_dialogo_colores(self):
        """Muestra el diálogo para configurar colores"""
        colores_actuales = self.parent_app.obtener_colores_guardados()
        dialog = DialogConfigurarColores(self, colores_actuales)
        if dialog.exec_() == QDialog.Accepted:
            self.parent_app.aplicar_colores(dialog.colores_seleccionados)
    
    def mostrar_configuraciones_avanzadas(self):
        """Muestra el diálogo de configuraciones avanzadas"""
        dialog = DialogConfiguracionesAvanzadas(self, self.parent_app)
        dialog.exec_()
    
    def mostrar_dialogo_eliminar(self):
        """Muestra un diálogo para seleccionar y eliminar una casilla"""
        if not self.parent_app.casillas:
            QMessageBox.information(self, "Sin casillas", "No hay casillas para eliminar.")
            return
        
        # Crear diálogo para seleccionar casilla
        dialog = QDialog(self)
        dialog.setWindowTitle("Eliminar Casilla")
        dialog.setFixedSize(350, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        label = QLabel("Selecciona la casilla que deseas eliminar:")
        layout.addWidget(label)
        
        # Lista de casillas
        lista_casillas = QListWidget()
        for nombre in sorted(self.parent_app.casillas.keys()):
            lista_casillas.addItem(nombre)
        lista_casillas.setCurrentRow(0)
        layout.addWidget(lista_casillas)
        
        label_info = QLabel(
            "⚠️ Los archivos de la casilla se moverán al escritorio\n"
            "y la carpeta será eliminada."
        )
        label_info.setWordWrap(True)
        label_info.setStyleSheet("color: #d32f2f; font-size: 10px;")
        layout.addWidget(label_info)
        
        # Botones
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialog.accept)
        botones.rejected.connect(dialog.reject)
        layout.addWidget(botones)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            item_seleccionado = lista_casillas.currentItem()
            if item_seleccionado:
                nombre_casilla = item_seleccionado.text()
                if nombre_casilla in self.parent_app.casillas:
                    self.parent_app.eliminar_casilla_completa(nombre_casilla)
    
    def buscar_archivos(self, texto):
        """Busca archivos en todas las carpetas de las casillas"""
        texto_buscar = texto.strip() if texto else ""
        
        if not texto_buscar:
            # Si está vacío, ocultar ventana de resultados
            self.ventana_resultados.hide()
            return
        
        texto_buscar = texto_buscar.lower()
        resultados = []
        
        # Buscar en todas las casillas
        for nombre_casilla, casilla in self.parent_app.casillas.items():
            carpeta = casilla.carpeta_path
            if not carpeta.exists():
                continue
            
            try:
                # Buscar archivos y carpetas recursivamente
                for item in carpeta.rglob('*'):
                    if item.name.lower().find(texto_buscar) != -1:
                        resultados.append({
                            'nombre': item.name,
                            'ruta': str(item),
                            'casilla': nombre_casilla,
                            'es_carpeta': item.is_dir()
                        })
            except Exception as e:
                print(f"Error al buscar en {carpeta}: {e}")
        
        # Mostrar resultados en la ventana
        if resultados:
            self.ventana_resultados.mostrar_resultados(resultados)
            # Posicionar la ventana debajo del panel de control
            pos_x = self.pos().x()
            pos_y = self.pos().y() + self.height() + 5
            self.ventana_resultados.move(pos_x, pos_y)
            self.ventana_resultados.show()
        else:
            self.ventana_resultados.mostrar_resultados([])
            pos_x = self.pos().x()
            pos_y = self.pos().y() + self.height() + 5
            self.ventana_resultados.move(pos_x, pos_y)
            self.ventana_resultados.show()
            
    def cerrar_aplicacion(self):
        """Cierra toda la aplicación"""
        self.parent_app.cerrar_todo()


class OrganizadorEscritorio:
    """Gestor principal del organizador de escritorio"""
    
    def __init__(self):
        self.casillas = {}
        self.carpeta_base = Path.home() / "Desktop" / "Organizador_Casillas"
        self.carpeta_base.mkdir(exist_ok=True)
        
        # Archivo para guardar posiciones
        self.archivo_config = Path.home() / "Desktop" / "Organizador_Casillas" / ".posiciones.json"
        self.posiciones = self.cargar_posiciones()
        
        # Detectar colores automáticamente si no hay colores guardados
        if not self.posiciones.get("colores"):
            self.detectar_colores_inicio()
        
        # Crear panel de control
        self.panel = PanelControl(self)
        self.panel.show()
        
        # Cargar casillas existentes
        self.cargar_casillas_existentes()
        
    def cargar_posiciones(self):
        """Carga las posiciones guardadas de las casillas y todas las configuraciones"""
        if self.archivo_config.exists():
            try:
                with open(self.archivo_config, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    # Asegurar que todas las claves existan para compatibilidad
                    if "casillas" not in datos:
                        datos["casillas"] = {}
                    if "tamanos" not in datos:
                        datos["tamanos"] = {}
                    if "tamanos_iconos" not in datos:
                        datos["tamanos_iconos"] = {}
                    if "configuraciones" not in datos:
                        datos["configuraciones"] = {}
                    if "colores" not in datos:
                        datos["colores"] = {}
                    if "estados" not in datos:
                        datos["estados"] = {}
                    if "panel" not in datos:
                        datos["panel"] = None
                    return datos
            except Exception as e:
                print(f"Error al cargar posiciones: {e}")
                return {"casillas": {}, "tamanos": {}, "tamanos_iconos": {}, "configuraciones": {}, "colores": {}, "estados": {}, "panel": None}
        return {"casillas": {}, "tamanos": {}, "tamanos_iconos": {}, "configuraciones": {}, "colores": {}, "estados": {}, "panel": None}
    
    def guardar_posiciones(self):
        """Guarda las posiciones de todas las casillas y todas las configuraciones"""
        posiciones_casillas = {}
        tamanos_casillas = {}
        tamanos_iconos_casillas = {}
        
        estados_casillas = {}  # Guardar estado expandido/colapsado
        
        for nombre, casilla in self.casillas.items():
            pos = casilla.pos()
            posiciones_casillas[nombre] = [pos.x(), pos.y()]
            
            # Guardar estado expandido/colapsado
            estados_casillas[nombre] = casilla.expandida
            
            # Guardar tamaños personalizados (colapsado y expandido)
            tamanos_casilla = {}
            if casilla.tamano_personalizado_colapsado:
                tamanos_casilla["colapsado"] = list(casilla.tamano_personalizado_colapsado)
            if casilla.tamano_personalizado_expandido:
                tamanos_casilla["expandido"] = list(casilla.tamano_personalizado_expandido)
            if tamanos_casilla:
                tamanos_casillas[nombre] = tamanos_casilla
            
            # Guardar tamaño de iconos de cada casilla
            tamanos_iconos_casillas[nombre] = casilla.tamano_iconos
        
        # Guardar tipos de vista de cada casilla
        tipos_vista_casillas = {}
        for nombre, casilla in self.casillas.items():
            tipos_vista_casillas[nombre] = casilla.tipo_vista
        
        # Combinar con las configuraciones existentes
        datos = {
            "casillas": posiciones_casillas,
            "tamanos": tamanos_casillas,
            "tamanos_iconos": tamanos_iconos_casillas,
            "tipos_vista": tipos_vista_casillas,  # Tipo de vista (lista/cuadrícula)
            "estados": estados_casillas,  # Estado expandido/colapsado
            "panel": [self.panel.pos().x(), self.panel.pos().y()] if self.panel else None
        }
        
        # Incluir configuraciones avanzadas si existen
        if "configuraciones" in self.posiciones:
            datos["configuraciones"] = self.posiciones["configuraciones"]
        
        # Incluir colores si existen
        if "colores" in self.posiciones:
            datos["colores"] = self.posiciones["colores"]
        
        try:
            with open(self.archivo_config, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2)
        except Exception as e:
            print(f"Error al guardar posiciones: {e}")
    
    def guardar_posicion_casilla(self, nombre, posicion):
        """Guarda la posición de una casilla específica"""
        if "casillas" not in self.posiciones:
            self.posiciones["casillas"] = {}
        self.posiciones["casillas"][nombre] = [posicion.x(), posicion.y()]
        self.guardar_posiciones()
    
    def guardar_posicion_panel(self, posicion):
        """Guarda la posición del panel"""
        self.posiciones["panel"] = [posicion.x(), posicion.y()]
        self.guardar_posiciones()
    
    def guardar_tamano_casilla(self, nombre, tamano, expandida):
        """Guarda el tamaño personalizado de una casilla (colapsado o expandido)"""
        if "tamanos" not in self.posiciones:
            self.posiciones["tamanos"] = {}
        if nombre not in self.posiciones["tamanos"]:
            self.posiciones["tamanos"][nombre] = {}
        
        if expandida:
            self.posiciones["tamanos"][nombre]["expandido"] = list(tamano)
        else:
            self.posiciones["tamanos"][nombre]["colapsado"] = list(tamano)
        self.guardar_posiciones()
    
    def guardar_tamano_iconos(self, nombre, tamano_iconos):
        """Guarda el tamaño de iconos de una casilla"""
        if "tamanos_iconos" not in self.posiciones:
            self.posiciones["tamanos_iconos"] = {}
        self.posiciones["tamanos_iconos"][nombre] = tamano_iconos
        self.guardar_posiciones()
    
    def guardar_tipo_vista(self, nombre, tipo_vista):
        """Guarda el tipo de vista de una casilla"""
        if "tipos_vista" not in self.posiciones:
            self.posiciones["tipos_vista"] = {}
        self.posiciones["tipos_vista"][nombre] = tipo_vista
        self.guardar_posiciones()
    
    def obtener_tipo_vista(self, nombre):
        """Obtiene el tipo de vista guardado para una casilla"""
        if "tipos_vista" in self.posiciones and nombre in self.posiciones["tipos_vista"]:
            return self.posiciones["tipos_vista"][nombre]
        # Si no hay tipo de vista guardado, usar el por defecto de configuraciones
        if "configuraciones" in self.posiciones:
            config = self.posiciones["configuraciones"]
            if "tipo_vista_defecto" in config:
                return config["tipo_vista_defecto"]
        return "lista"  # Por defecto lista si no hay configuración
    
    def obtener_tamano_iconos(self, nombre):
        """Obtiene el tamaño de iconos guardado para una casilla"""
        if "tamanos_iconos" in self.posiciones and nombre in self.posiciones["tamanos_iconos"]:
            return self.posiciones["tamanos_iconos"][nombre]
        return None
    
    def guardar_colores(self, colores):
        """Guarda los colores personalizados en el archivo de configuración"""
        if "colores" not in self.posiciones:
            self.posiciones["colores"] = {}
        self.posiciones["colores"] = {k: list(v) for k, v in colores.items()}
        # Guardar directamente sin llamar a guardar_posiciones si el panel no existe aún
        try:
            self.guardar_posiciones()
        except AttributeError:
            # Si el panel no existe aún, guardar solo los colores
            datos = {
                "casillas": self.posiciones.get("casillas", {}),
                "tamanos": self.posiciones.get("tamanos", {}),
                "colores": self.posiciones["colores"],
                "panel": self.posiciones.get("panel")
            }
            try:
                with open(self.archivo_config, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, indent=2)
            except Exception as e:
                print(f"Error al guardar colores: {e}")
    
    def obtener_colores_guardados(self):
        """Obtiene los colores guardados del archivo de configuración"""
        colores = self.posiciones.get("colores", {})
        # Convertir listas a tuplas para mantener consistencia
        return {k: tuple(v) if isinstance(v, list) else v for k, v in colores.items()}
    
    def aplicar_colores(self, colores):
        """Aplica los colores personalizados a todas las casillas existentes"""
        # Guardar colores
        self.guardar_colores(colores)
        
        # Aplicar a todas las casillas existentes
        for casilla in self.casillas.values():
            casilla.aplicar_colores(colores)
    
    def detectar_colores_inicio(self):
        """Detecta automáticamente los colores del fondo al iniciar la aplicación"""
        ruta_fondo = obtener_ruta_fondo_escritorio()
        if not ruta_fondo:
            return
        
        colores_dominantes = analizar_colores_imagen(ruta_fondo)
        if not colores_dominantes:
            return
        
        paleta = generar_paleta_colores(colores_dominantes)
        if paleta:
            # Guardar y aplicar sin mostrar mensajes
            self.guardar_colores(paleta)
    
    def crear_casilla(self, nombre):
        """Crea una nueva casilla y su carpeta correspondiente"""
        if not nombre:
            QMessageBox.warning(self.panel, "Advertencia", "Por favor ingresa un nombre para la casilla.")
            return
            
        if nombre in self.casillas:
            QMessageBox.warning(self.panel, "Advertencia", f"Ya existe una casilla con el nombre '{nombre}'.")
            return
            
        # Crear carpeta
        carpeta_path = self.carpeta_base / nombre
        try:
            carpeta_path.mkdir(exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.panel, "Error", f"No se pudo crear la carpeta: {str(e)}")
            return
            
        # Obtener posición guardada o usar posición por defecto
        posicion = None
        if nombre in self.posiciones.get("casillas", {}):
            pos = self.posiciones["casillas"][nombre]
            posicion = (pos[0], pos[1])
        else:
            # Posición por defecto (distribuir en diagonal)
            screen = QApplication.primaryScreen().geometry()
            offset_x = len(self.casillas) * 200
            offset_y = len(self.casillas) * 150
            posicion = (100 + offset_x, 100 + offset_y)
        
        # Obtener tamaños personalizados si existen
        tamano_colapsado = None
        tamano_expandido = None
        if nombre in self.posiciones.get("tamanos", {}):
            tamanos = self.posiciones["tamanos"][nombre]
            # Compatibilidad con formato antiguo (lista simple)
            if isinstance(tamanos, list):
                tamano_colapsado = (tamanos[0], tamanos[1])
            else:
                # Formato nuevo (diccionario con colapsado y expandido)
                if "colapsado" in tamanos:
                    tamano_colapsado = (tamanos["colapsado"][0], tamanos["colapsado"][1])
                if "expandido" in tamanos:
                    tamano_expandido = (tamanos["expandido"][0], tamanos["expandido"][1])
            
        # Obtener tamaños por defecto de configuraciones si no hay tamaños personalizados
        if not tamano_colapsado and "configuraciones" in self.posiciones:
            config = self.posiciones["configuraciones"]
            if "tamano_colapsado_defecto" in config:
                tamano_colapsado = tuple(config["tamano_colapsado_defecto"])
        if not tamano_expandido and "configuraciones" in self.posiciones:
            config = self.posiciones["configuraciones"]
            if "tamano_expandido_defecto" in config:
                tamano_expandido = tuple(config["tamano_expandido_defecto"])
        
        # Crear ventana de casilla
        casilla = CasillaVentana(nombre, carpeta_path, posicion, self)
        if tamano_colapsado:
            casilla.tamano_personalizado_colapsado = tamano_colapsado
            # Aplicar tamaño personalizado colapsado después de que la UI esté lista
            QApplication.processEvents()
            casilla.resize(tamano_colapsado[0], tamano_colapsado[1])
        if tamano_expandido:
            casilla.tamano_personalizado_expandido = tamano_expandido
        
        # Cargar tamaño de iconos personalizado si existe, sino usar el por defecto
        tamano_iconos = self.obtener_tamano_iconos(nombre)
        if tamano_iconos:
            casilla.tamano_iconos = tamano_iconos
        elif "configuraciones" in self.posiciones:
            # Si no hay tamaño personalizado, usar el por defecto
            config = self.posiciones["configuraciones"]
            if "tamano_iconos_defecto" in config:
                casilla.tamano_iconos = config["tamano_iconos_defecto"]
        
        # Aplicar el tamaño de iconos y actualizar la lista
        casilla.actualizar_tamano_iconos()
        QApplication.processEvents()
        casilla.actualizar_lista_archivos()
        
        # Aplicar multiplicador de resolución por defecto si existe
        if "configuraciones" in self.posiciones:
            config = self.posiciones["configuraciones"]
            if "multiplicador_resolucion_iconos" in config:
                casilla.multiplicador_resolucion_iconos = config["multiplicador_resolucion_iconos"]
            # Aplicar velocidad de scroll por defecto si existe
            if "velocidad_scroll" in config:
                casilla.velocidad_scroll = config["velocidad_scroll"]
                casilla.actualizar_velocidad_scroll()
        
        # Aplicar tipo de vista (obtener_tipo_vista ya maneja el por defecto)
        tipo_vista = self.obtener_tipo_vista(nombre)
        casilla.tipo_vista = tipo_vista
        casilla.aplicar_tipo_vista()
        
        # Aplicar colores personalizados si existen
        colores = self.obtener_colores_guardados()
        if colores:
            casilla.aplicar_colores(colores)
        
        casilla.archivo_soltado.connect(self.mover_archivo)
        casilla.casilla_eliminada.connect(self.eliminar_casilla)
        casilla.show()
        casilla.raise_()  # Asegurar que esté al frente
        casilla.activateWindow()  # Activar la ventana
        
        self.casillas[nombre] = casilla
        
    def mover_archivo(self, archivo_path, nombre_casilla):
        """Mueve un archivo o carpeta a la carpeta de la casilla"""
        try:
            elemento_origen = Path(archivo_path)
            carpeta_destino = self.casillas[nombre_casilla].carpeta_path
            nombre_elemento = elemento_origen.name
            destino = carpeta_destino / nombre_elemento
            
            # Si el elemento ya existe, agregar un número
            contador = 1
            if elemento_origen.is_file():
                # Es un archivo: manejar extensión
                nombre_base, extension = os.path.splitext(nombre_elemento)
                while destino.exists():
                    nuevo_nombre = f"{nombre_base}_{contador}{extension}"
                    destino = carpeta_destino / nuevo_nombre
                    contador += 1
            else:
                # Es una carpeta: no tiene extensión
                nombre_base = nombre_elemento
                while destino.exists():
                    nuevo_nombre = f"{nombre_base}_{contador}"
                    destino = carpeta_destino / nuevo_nombre
                    contador += 1
                
            shutil.move(str(elemento_origen), str(destino))
            # Actualizar la lista de archivos en la casilla
            if nombre_casilla in self.casillas:
                self.casillas[nombre_casilla].actualizar_lista_archivos()
            
            # Mensaje eliminado - el movimiento se realiza silenciosamente
        except Exception as e:
            QMessageBox.critical(self.panel, "Error", f"No se pudo mover: {str(e)}")
    
    def mover_archivo_entre_casillas(self, archivo_path, nombre_casilla_origen, nombre_casilla_destino):
        """Mueve un archivo de una casilla a otra"""
        try:
            elemento_origen = Path(archivo_path)
            carpeta_destino = self.casillas[nombre_casilla_destino].carpeta_path
            nombre_elemento = elemento_origen.name
            destino = carpeta_destino / nombre_elemento
            
            # Si el elemento ya existe, agregar un número
            contador = 1
            if elemento_origen.is_file():
                # Es un archivo: manejar extensión
                nombre_base, extension = os.path.splitext(nombre_elemento)
                while destino.exists():
                    nuevo_nombre = f"{nombre_base}_{contador}{extension}"
                    destino = carpeta_destino / nuevo_nombre
                    contador += 1
            else:
                # Es una carpeta: no tiene extensión
                nombre_base = nombre_elemento
                while destino.exists():
                    nuevo_nombre = f"{nombre_base}_{contador}"
                    destino = carpeta_destino / nuevo_nombre
                    contador += 1
                
            shutil.move(str(elemento_origen), str(destino))
            
            # Actualizar las listas de archivos en ambas casillas
            if nombre_casilla_origen in self.casillas:
                self.casillas[nombre_casilla_origen].actualizar_lista_archivos()
            if nombre_casilla_destino in self.casillas:
                self.casillas[nombre_casilla_destino].actualizar_lista_archivos()
            
            # Mensaje eliminado - el movimiento se realiza silenciosamente
        except Exception as e:
            QMessageBox.critical(self.panel, "Error", f"No se pudo mover: {str(e)}")
    
    def mover_archivo_al_escritorio(self, archivo_path):
        """Mueve un archivo de una casilla al escritorio"""
        try:
            elemento_origen = Path(archivo_path)
            ruta_escritorio = self.obtener_ruta_escritorio()
            nombre_elemento = elemento_origen.name
            destino = ruta_escritorio / nombre_elemento
            
            # Si el elemento ya existe, agregar un número
            contador = 1
            if elemento_origen.is_file():
                # Es un archivo: manejar extensión
                nombre_base, extension = os.path.splitext(nombre_elemento)
                while destino.exists():
                    nuevo_nombre = f"{nombre_base} ({contador}){extension}"
                    destino = ruta_escritorio / nuevo_nombre
                    contador += 1
            else:
                # Es una carpeta: no tiene extensión
                nombre_base = nombre_elemento
                while destino.exists():
                    nuevo_nombre = f"{nombre_base} ({contador})"
                    destino = ruta_escritorio / nuevo_nombre
                    contador += 1
                
            shutil.move(str(elemento_origen), str(destino))
            
            # Actualizar la lista de archivos en la casilla de origen
            for nombre, casilla in self.casillas.items():
                if elemento_origen.parent == casilla.carpeta_path:
                    casilla.actualizar_lista_archivos()
                    break
            
            # Mensaje eliminado - el movimiento se realiza silenciosamente
        except Exception as e:
            QMessageBox.critical(self.panel, "Error", f"No se pudo mover: {str(e)}")
            
    def obtener_ruta_escritorio(self):
        """Obtiene la ruta del escritorio del usuario"""
        try:
            # Intentar obtener la ruta del escritorio desde el registro de Windows
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            winreg.CloseKey(key)
            return Path(desktop_path)
        except:
            # Si falla, usar la ruta por defecto
            return Path.home() / "Desktop"
    
    def eliminar_casilla_completa(self, nombre_casilla):
        """Elimina una casilla completamente, moviendo sus archivos al escritorio"""
        if nombre_casilla not in self.casillas:
            QMessageBox.warning(self.panel, "Error", f"La casilla '{nombre_casilla}' no existe.")
            return
        
        casilla = self.casillas[nombre_casilla]
        carpeta_casilla = casilla.carpeta_path
        ruta_escritorio = self.obtener_ruta_escritorio()
        
        # Confirmar eliminación
        respuesta = QMessageBox.question(
            self.panel,
            "Confirmar eliminación",
            f"¿Eliminar la casilla '{nombre_casilla}'?\n\n"
            f"Los archivos de la casilla se moverán al escritorio:\n{ruta_escritorio}\n\n"
            f"La carpeta de la casilla será eliminada.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if respuesta != QMessageBox.Yes:
            return
        
        # Mover archivos al escritorio
        archivos_movidos = 0
        errores = []
        
        if carpeta_casilla.exists() and carpeta_casilla.is_dir():
            try:
                # Mover todos los archivos y carpetas al escritorio
                for elemento in carpeta_casilla.iterdir():
                    try:
                        destino = ruta_escritorio / elemento.name
                        
                        # Si ya existe un archivo con el mismo nombre, agregar un número
                        contador = 1
                        nombre_base = elemento.stem
                        extension = elemento.suffix
                        while destino.exists():
                            if elemento.is_dir():
                                nuevo_nombre = f"{nombre_base} ({contador})"
                            else:
                                nuevo_nombre = f"{nombre_base} ({contador}){extension}"
                            destino = ruta_escritorio / nuevo_nombre
                            contador += 1
                        
                        # Mover el elemento
                        shutil.move(str(elemento), str(destino))
                        archivos_movidos += 1
                    except Exception as e:
                        errores.append(f"{elemento.name}: {str(e)}")
                
                # Eliminar la carpeta vacía
                try:
                    carpeta_casilla.rmdir()
                except Exception as e:
                    errores.append(f"No se pudo eliminar la carpeta: {str(e)}")
                    
            except Exception as e:
                errores.append(f"Error al mover archivos: {str(e)}")
        
        # Cerrar la ventana de la casilla
        casilla.close()
        
        # Eliminar del diccionario
        del self.casillas[nombre_casilla]
        
        # Eliminar todas las configuraciones guardadas de esta casilla
        if "casillas" in self.posiciones and nombre_casilla in self.posiciones["casillas"]:
            del self.posiciones["casillas"][nombre_casilla]
        
        if "tamanos" in self.posiciones and nombre_casilla in self.posiciones["tamanos"]:
            del self.posiciones["tamanos"][nombre_casilla]
        
        if "tamanos_iconos" in self.posiciones and nombre_casilla in self.posiciones["tamanos_iconos"]:
            del self.posiciones["tamanos_iconos"][nombre_casilla]
        
        self.guardar_posiciones()
        
        # Mostrar mensaje de resultado
        mensaje = f"Casilla '{nombre_casilla}' eliminada.\n\n"
        mensaje += f"Archivos movidos al escritorio: {archivos_movidos}"
        
        if errores:
            mensaje += f"\n\nErrores encontrados:\n" + "\n".join(errores[:5])
            if len(errores) > 5:
                mensaje += f"\n... y {len(errores) - 5} más"
        
        QMessageBox.information(self.panel, "Casilla Eliminada", mensaje)
    
    def eliminar_casilla(self, casilla):
        """Elimina una casilla (método antiguo, ahora usa eliminar_casilla_completa)"""
        self.eliminar_casilla_completa(casilla.nombre)
            
    def cargar_casillas_existentes(self):
        """Carga las casillas existentes basadas en las carpetas"""
        if not self.carpeta_base.exists():
            return
            
        for carpeta in self.carpeta_base.iterdir():
            if carpeta.is_dir() and not carpeta.name.startswith('.'):
                nombre = carpeta.name
                
                # Obtener posición guardada
                posicion = None
                if nombre in self.posiciones.get("casillas", {}):
                    pos = self.posiciones["casillas"][nombre]
                    posicion = (pos[0], pos[1])
                else:
                    # Posición por defecto
                    screen = QApplication.primaryScreen().geometry()
                    offset_x = len(self.casillas) * 200
                    offset_y = len(self.casillas) * 150
                    posicion = (100 + offset_x, 100 + offset_y)
                
                # Obtener tamaños personalizados si existen
                tamano_colapsado = None
                tamano_expandido = None
                if nombre in self.posiciones.get("tamanos", {}):
                    tamanos = self.posiciones["tamanos"][nombre]
                    # Compatibilidad con formato antiguo (lista simple)
                    if isinstance(tamanos, list):
                        tamano_colapsado = (tamanos[0], tamanos[1])
                    else:
                        # Formato nuevo (diccionario con colapsado y expandido)
                        if "colapsado" in tamanos:
                            tamano_colapsado = (tamanos["colapsado"][0], tamanos["colapsado"][1])
                        if "expandido" in tamanos:
                            tamano_expandido = (tamanos["expandido"][0], tamanos["expandido"][1])
                
                # Crear ventana de casilla
                casilla = CasillaVentana(nombre, carpeta, posicion, self)
                if tamano_colapsado:
                    casilla.tamano_personalizado_colapsado = tamano_colapsado
                    # Aplicar tamaño personalizado colapsado después de que la UI esté lista
                    QApplication.processEvents()
                    casilla.resize(tamano_colapsado[0], tamano_colapsado[1])
                if tamano_expandido:
                    casilla.tamano_personalizado_expandido = tamano_expandido
                
                # Cargar tamaño de iconos personalizado si existe, sino usar el por defecto
                tamano_iconos = self.obtener_tamano_iconos(nombre)
                if tamano_iconos:
                    casilla.tamano_iconos = tamano_iconos
                elif "configuraciones" in self.posiciones:
                    # Si no hay tamaño personalizado, usar el por defecto
                    config = self.posiciones["configuraciones"]
                    if "tamano_iconos_defecto" in config:
                        casilla.tamano_iconos = config["tamano_iconos_defecto"]
                
                # Aplicar el tamaño de iconos y actualizar la lista
                casilla.actualizar_tamano_iconos()
                QApplication.processEvents()
                casilla.actualizar_lista_archivos()
                
                # Aplicar multiplicador de resolución por defecto si existe
                if "configuraciones" in self.posiciones:
                    config = self.posiciones["configuraciones"]
                    if "multiplicador_resolucion_iconos" in config:
                        casilla.multiplicador_resolucion_iconos = config["multiplicador_resolucion_iconos"]
                    # Aplicar velocidad de scroll por defecto si existe
                    if "velocidad_scroll" in config:
                        casilla.velocidad_scroll = config["velocidad_scroll"]
                        casilla.actualizar_velocidad_scroll()
                
                # Aplicar tipo de vista (obtener_tipo_vista ya maneja el por defecto)
                tipo_vista = self.obtener_tipo_vista(nombre)
                casilla.tipo_vista = tipo_vista
                casilla.aplicar_tipo_vista()
                
                # Restaurar estado expandido/colapsado si existe
                estados = self.posiciones.get("estados", {})
                if nombre in estados and estados[nombre]:
                    # Si estaba expandida, expandirla después de aplicar los tamaños
                    QApplication.processEvents()
                    if not casilla.expandida:
                        casilla.toggle_expandir()
                
                # Aplicar colores personalizados si existen
                colores = self.obtener_colores_guardados()
                if colores:
                    casilla.aplicar_colores(colores)
                
                casilla.archivo_soltado.connect(self.mover_archivo)
                casilla.casilla_eliminada.connect(self.eliminar_casilla)
                casilla.show()
                casilla.raise_()  # Asegurar que esté al frente
                casilla.activateWindow()  # Activar la ventana
                
                self.casillas[nombre] = casilla
        
        # Restaurar posición del panel
        if self.posiciones.get("panel"):
            pos = self.posiciones["panel"]
            self.panel.move(pos[0], pos[1])
    
    def cerrar_todo(self):
        """Cierra todas las ventanas y la aplicación"""
        self.guardar_posiciones()
        for casilla in self.casillas.values():
            casilla.close()
        self.panel.close()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # No cerrar cuando se cierra una ventana
    
    organizador = OrganizadorEscritorio()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
