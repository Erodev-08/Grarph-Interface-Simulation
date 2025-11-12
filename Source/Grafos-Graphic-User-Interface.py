import sys
import json
import uuid
import itertools
import math
from typing import Dict, List, Tuple, Optional, Set
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QDockWidget, QListWidget, QToolBar,
    QAction, QActionGroup, QDialog, QFormLayout, QSpinBox, QDoubleSpinBox,
    QColorDialog, QGroupBox, QRadioButton, QTabWidget, QToolButton, QLayout,
    QSlider, QScrollArea, QMenuBar, QMenu, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTreeWidget, QTreeWidgetItem, QProgressDialog,
    QShortcut, QStyle
)
from PyQt5.QtWidgets import QInputDialog, QListWidgetItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QSettings, QSize
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QIcon, QPalette,
    QMouseEvent, QWheelEvent, QKeyEvent, QPainterPath, QLinearGradient,
    QKeySequence
)
try:
    # SVG export support (optional)
    from PyQt5.QtSvg import QSvgGenerator
    HAS_QTSVG = True
except Exception:
    HAS_QTSVG = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("Warning: NetworkX not available. Some features will be disabled.")

try:
    from ursina import *
    HAS_URSINA = True
except ImportError:
    HAS_URSINA = False
    print("Warning: Ursina not available. 3D visualization will be disabled.")


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class NodeData:
    """Node data structure"""
    id: str
    label: str
    pos: Tuple[float, float]
    color: Tuple[int, int, int] = (100, 180, 255)
    size: float = 20.0
    
    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'pos': list(self.pos),
            'color': list(self.color),
            'size': self.size
        }
    
    @staticmethod
    def from_dict(data):
        return NodeData(
            id=data['id'],
            label=data['label'],
            pos=tuple(data['pos']),
            color=tuple(data.get('color', (100, 180, 255))),
            size=data.get('size', 20.0)
        )


@dataclass
class EdgeData:
    """Edge data structure"""
    id: str
    source: str
    target: str
    weight: float = 1.0
    label: str = ""
    color: Tuple[int, int, int] = (60, 60, 60)
    directed: bool = False
    
    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'target': self.target,
            'weight': self.weight,
            'label': self.label,
            'color': list(self.color),
            'directed': self.directed
        }
    
    @staticmethod
    def from_dict(data):
        return EdgeData(
            id=data['id'],
            source=data['source'],
            target=data['target'],
            weight=data.get('weight', 1.0),
            label=data.get('label', ''),
            color=tuple(data.get('color', (60, 60, 60))),
            directed=data.get('directed', False)
        )


# ============================================================================
# PREFERENCES DIALOG
# ============================================================================

class PreferencesDialog(QDialog):
    """Preferences and settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferencias y Configuración")
        self.setMinimumWidth(500)
        self.settings = QSettings('GraphGUI', 'Preferences')
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Appearance Tab
        appearance_tab = QWidget()
        appearance_layout = QFormLayout(appearance_tab)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        appearance_layout.addRow("Tema:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        appearance_layout.addRow("Tamaño de fuente:", self.font_size_spin)
        
        tabs.addTab(appearance_tab, "Apariencia")
        
        # Grid Tab
        grid_tab = QWidget()
        grid_layout = QFormLayout(grid_tab)
        
        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(10, 100)
        self.grid_size_spin.setValue(20)
        grid_layout.addRow("Tamaño de rejilla:", self.grid_size_spin)
        
        self.grid_visible_check = QCheckBox()
        self.grid_visible_check.setChecked(True)
        grid_layout.addRow("Rejilla visible:", self.grid_visible_check)
        
        self.snap_to_grid_check = QCheckBox()
        self.snap_to_grid_check.setChecked(True)
        grid_layout.addRow("Ajustar a rejilla:", self.snap_to_grid_check)
        
        tabs.addTab(grid_tab, "Rejilla")
        
        # Nodes Tab
        nodes_tab = QWidget()
        nodes_layout = QFormLayout(nodes_tab)
        
        self.node_size_spin = QDoubleSpinBox()
        self.node_size_spin.setRange(10.0, 50.0)
        self.node_size_spin.setValue(20.0)
        nodes_layout.addRow("Tamaño de nodo:", self.node_size_spin)
        
        self.node_color_btn = QPushButton("Seleccionar color")
        self.node_color = QColor(100, 180, 255)
        self.node_color_btn.clicked.connect(self.choose_node_color)
        nodes_layout.addRow("Color de nodo:", self.node_color_btn)
        
        self.auto_label_check = QCheckBox()
        self.auto_label_check.setChecked(True)
        nodes_layout.addRow("Etiquetas automáticas:", self.auto_label_check)
        
        tabs.addTab(nodes_tab, "Nodos")
        
        # Edges Tab
        edges_tab = QWidget()
        edges_layout = QFormLayout(edges_tab)
        
        self.edge_weight_spin = QDoubleSpinBox()
        self.edge_weight_spin.setRange(0.1, 100.0)
        self.edge_weight_spin.setValue(1.0)
        edges_layout.addRow("Peso predeterminado:", self.edge_weight_spin)
        
        self.edge_color_btn = QPushButton("Seleccionar color")
        self.edge_color = QColor(60, 60, 60)
        self.edge_color_btn.clicked.connect(self.choose_edge_color)
        edges_layout.addRow("Color de arista:", self.edge_color_btn)
        
        self.directed_check = QCheckBox()
        self.directed_check.setChecked(False)
        edges_layout.addRow("Aristas dirigidas:", self.directed_check)
        
        tabs.addTab(edges_tab, "Aristas")
        
        # Algorithm Tab
        algo_tab = QWidget()
        algo_layout = QFormLayout(algo_tab)
        
        self.anim_speed_slider = QSlider(Qt.Horizontal)
        self.anim_speed_slider.setRange(1, 10)
        self.anim_speed_slider.setValue(5)
        self.anim_speed_label = QLabel("5")
        self.anim_speed_slider.valueChanged.connect(
            lambda v: self.anim_speed_label.setText(str(v))
        )
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.anim_speed_slider)
        speed_layout.addWidget(self.anim_speed_label)
        algo_layout.addRow("Velocidad de animación:", speed_layout)
        
        self.highlight_path_check = QCheckBox()
        self.highlight_path_check.setChecked(True)
        algo_layout.addRow("Resaltar caminos:", self.highlight_path_check)

        self.curved_multiedges_check = QCheckBox()
        self.curved_multiedges_check.setChecked(True)
        algo_layout.addRow("Curvar aristas paralelas:", self.curved_multiedges_check)
        
        tabs.addTab(algo_tab, "Algoritmos")
        
        # 3D View Tab
        view3d_tab = QWidget()
        view3d_layout = QFormLayout(view3d_tab)
        
        self.lighting_check = QCheckBox()
        self.lighting_check.setChecked(True)
        view3d_layout.addRow("Iluminación mejorada:", self.lighting_check)
        
        self.shadows_check = QCheckBox()
        self.shadows_check.setChecked(True)
        view3d_layout.addRow("Sombras:", self.shadows_check)
        
        self.sky_check = QCheckBox()
        self.sky_check.setChecked(True)
        view3d_layout.addRow("Cielo texturizado:", self.sky_check)
        
        tabs.addTab(view3d_tab, "Vista 3D")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Restaurar predeterminados")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Aceptar")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def choose_node_color(self):
        color = QColorDialog.getColor(self.node_color, self)
        if color.isValid():
            self.node_color = color
            self.node_color_btn.setStyleSheet(
                f"background-color: {color.name()};"
            )
    
    def choose_edge_color(self):
        color = QColorDialog.getColor(self.edge_color, self)
        if color.isValid():
            self.edge_color = color
            self.edge_color_btn.setStyleSheet(
                f"background-color: {color.name()};"
            )
    
    def load_settings(self):
        """Load settings from QSettings"""
        self.theme_combo.setCurrentText(
            self.settings.value('theme', 'Light')
        )
        self.font_size_spin.setValue(
            int(self.settings.value('font_size', 10))
        )
        self.grid_size_spin.setValue(
            int(self.settings.value('grid_size', 20))
        )
        self.grid_visible_check.setChecked(
            self.settings.value('grid_visible', True, type=bool)
        )
        self.snap_to_grid_check.setChecked(
            self.settings.value('snap_to_grid', True, type=bool)
        )
        self.node_size_spin.setValue(
            float(self.settings.value('node_size', 20.0))
        )
        
        node_color = self.settings.value('node_color', '#64B4FF')
        self.node_color = QColor(node_color)
        self.node_color_btn.setStyleSheet(f"background-color: {node_color};")
        
        self.auto_label_check.setChecked(
            self.settings.value('auto_label', True, type=bool)
        )
        self.edge_weight_spin.setValue(
            float(self.settings.value('edge_weight', 1.0))
        )
        
        edge_color = self.settings.value('edge_color', '#3C3C3C')
        self.edge_color = QColor(edge_color)
        self.edge_color_btn.setStyleSheet(f"background-color: {edge_color};")
        
        self.directed_check.setChecked(
            self.settings.value('directed', False, type=bool)
        )
        self.anim_speed_slider.setValue(
            int(self.settings.value('anim_speed', 5))
        )
        self.curved_multiedges_check.setChecked(
            self.settings.value('curved_multiedges', True, type=bool)
        )
        self.highlight_path_check.setChecked(
            self.settings.value('highlight_path', True, type=bool)
        )
        self.lighting_check.setChecked(
            self.settings.value('lighting', True, type=bool)
        )
        self.shadows_check.setChecked(
            self.settings.value('shadows', True, type=bool)
        )
        self.sky_check.setChecked(
            self.settings.value('sky', True, type=bool)
        )
    
    def save_settings(self):
        """Save settings to QSettings"""
        self.settings.setValue('theme', self.theme_combo.currentText())
        self.settings.setValue('font_size', self.font_size_spin.value())
        self.settings.setValue('grid_size', self.grid_size_spin.value())
        self.settings.setValue('grid_visible', self.grid_visible_check.isChecked())
        self.settings.setValue('snap_to_grid', self.snap_to_grid_check.isChecked())
        self.settings.setValue('node_size', self.node_size_spin.value())
        self.settings.setValue('node_color', self.node_color.name())
        self.settings.setValue('auto_label', self.auto_label_check.isChecked())
        self.settings.setValue('edge_weight', self.edge_weight_spin.value())
        self.settings.setValue('edge_color', self.edge_color.name())
        self.settings.setValue('directed', self.directed_check.isChecked())
        self.settings.setValue('anim_speed', self.anim_speed_slider.value())
        self.settings.setValue('curved_multiedges', self.curved_multiedges_check.isChecked())
        self.settings.setValue('highlight_path', self.highlight_path_check.isChecked())
        self.settings.setValue('lighting', self.lighting_check.isChecked())
        self.settings.setValue('shadows', self.shadows_check.isChecked())
        self.settings.setValue('sky', self.sky_check.isChecked())
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            'Restaurar predeterminados',
            '¿Está seguro de que desea restaurar todas las configuraciones a sus valores predeterminados?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self.load_settings()
    
    def accept(self):
        self.save_settings()
        super().accept()


# ============================================================================
# GRAPH CANVAS
# ============================================================================

class GraphCanvas(QWidget):
    """Interactive canvas for graph visualization"""
    
    node_selected = pyqtSignal(str)  # node_id
    edge_selected = pyqtSignal(str)  # edge_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Graph data
        self.nodes: Dict[str, NodeData] = {}
        self.edges: Dict[str, EdgeData] = {}
        
        # View state
        self.offset = QPointF(0, 0)
        self.zoom = 1.0
        self.grid_size = 20
        self.show_grid = True
        self.snap_to_grid = True
        
        # Interaction state
        self.mode = 'select'  # 'select' or 'connect'
        self.selected_nodes: Set[str] = set()
        self.selected_edges: Set[str] = set()
        self.hovered_node: Optional[str] = None
        self.hovered_edge: Optional[str] = None
        self.dragging_node: Optional[str] = None
        self.drag_start: Optional[QPointF] = None
        self.panning = False
        self.pan_start: Optional[QPointF] = None
        self.connect_source: Optional[str] = None
        
        # Highlighting
        self.highlighted_nodes: Set[str] = set()
        self.highlighted_edges: Set[str] = set()
        
        # Settings
        self.settings = QSettings('GraphGUI', 'Preferences')
        self.load_preferences()
        
        # Auto-label counter
        self.node_counter = 0

        self.animation_controller = AnimationController(self)
        # --- Mejoras de arrastre ---
        self.drag_threshold = 4  # píxeles antes de activar movimiento real
        self.dragging_initiated = False
        self.group_drag_orig_positions = {}
        # Selección rectangular
        self.selection_box_active = False
        self.selection_box_start = None
        self.selection_box_current = None
    
    def load_preferences(self):
        """Load preferences from settings"""
        self.grid_size = int(self.settings.value('grid_size', 20))
        self.show_grid = self.settings.value('grid_visible', True, type=bool)
        self.snap_to_grid = self.settings.value('snap_to_grid', True, type=bool)
    
    def screen_to_world(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to world coordinates"""
        return QPointF(
            (screen_pos.x() - self.offset.x()) / self.zoom,
            (screen_pos.y() - self.offset.y()) / self.zoom
        )
    
    def world_to_screen(self, world_pos: Tuple[float, float]) -> QPointF:
        """Convert world coordinates to screen coordinates"""
        return QPointF(
            world_pos[0] * self.zoom + self.offset.x(),
            world_pos[1] * self.zoom + self.offset.y()
        )
    
    def snap_to_grid_pos(self, pos: QPointF) -> QPointF:
        """Snap position to grid"""
        if self.snap_to_grid:
            return QPointF(
                round(pos.x() / self.grid_size) * self.grid_size,
                round(pos.y() / self.grid_size) * self.grid_size
            )
        return pos
    
    def add_node(self, pos: Tuple[float, float], label: str = None) -> str:
        """Add a new node"""
        # Validate label
        if label is None:
            if self.settings.value('auto_label', True, type=bool):
                self.node_counter += 1
                label = f"N{self.node_counter}"
            else:
                label = ""
        
        # Check for duplicate labels
        if label and any(n.label == label for n in self.nodes.values()):
            QMessageBox.warning(
                self,
                "Etiqueta duplicada",
                f"Ya existe un nodo con la etiqueta '{label}'."
            )
            return None
        
        node_id = str(uuid.uuid4())
        color = self.settings.value('node_color', '#64B4FF')
        color_rgb = QColor(color).getRgb()[:3]
        size = float(self.settings.value('node_size', 20.0))
        
        self.nodes[node_id] = NodeData(
            id=node_id,
            label=label,
            pos=pos,
            color=color_rgb,
            size=size
        )
        
        self.update()
        return node_id
    
    def remove_node(self, node_id: str):
        """Remove a node and its connected edges"""
        if node_id not in self.nodes:
            return
        
        # Remove connected edges
        edges_to_remove = [
            eid for eid, edge in self.edges.items()
            if edge.source == node_id or edge.target == node_id
        ]
        for eid in edges_to_remove:
            del self.edges[eid]
        
        # Remove node
        del self.nodes[node_id]
        
        # Clear selection
        self.selected_nodes.discard(node_id)
        
        self.update()
    
    def add_edge(self, source: str, target: str, weight: float = None, directed: bool = None) -> str:
        """Add a new edge"""
        # Validate nodes exist
        if source not in self.nodes or target not in self.nodes:
            QMessageBox.warning(
                self,
                "Nodos inválidos",
                "Los nodos de origen y destino deben existir."
            )
            return None
        
        # Validate no self-loops
        if source == target:
            QMessageBox.warning(
                self,
                "Auto-bucle no permitido",
                "No se pueden crear aristas de un nodo a sí mismo."
            )
            return None
        
        # Support for global directed mode & multigraph option
        # Bandera global (fallback a configuración si aún no creada)
        allow_multigraph = getattr(self.parent(), 'allow_multigraph', False) if self.parent() else False
        global_directed = getattr(self.parent(), 'graph_directed', None)
        if directed is None:
            if global_directed is not None:
                directed = global_directed
            else:
                directed = self.settings.value('directed', False, type=bool)

        if not allow_multigraph:
            # Reglas anti-duplicados (como antes) sólo si NO es multigrafo
            for edge in self.edges.values():
                same_pair_ignoring_dir = {edge.source, edge.target} == {source, target}
                if not directed:
                    if same_pair_ignoring_dir:
                        QMessageBox.warning(
                            self,
                            "Arista duplicada",
                            "Ya existe una conexión entre estos nodos. (Activar multigrafo para permitirla)"
                        )
                        return None
                else:
                    if edge.directed and edge.source == source and edge.target == target:
                        QMessageBox.warning(
                            self,
                            "Arista duplicada",
                            "Ya existe una arista dirigida con la misma dirección. (Multigrafo permitiría crear otra)"
                        )
                        return None
        
        if weight is None:
            weight = float(self.settings.value('edge_weight', 1.0))
        
        # directed ya resuelto arriba si era None
        
        # Validate weight
        if weight <= 0:
            QMessageBox.warning(
                self,
                "Peso inválido",
                "El peso de la arista debe ser mayor que cero."
            )
            return None
        
        edge_id = str(uuid.uuid4())
        color = self.settings.value('edge_color', '#3C3C3C')
        color_rgb = QColor(color).getRgb()[:3]
        
        # Etiqueta por defecto: si hay multigrafo, incluir índice secuencial para distinguir
        if allow_multigraph:
            parallel_count = sum(1 for e in self.edges.values() if {e.source, e.target} == {source, target})
            default_label = f"{weight:.1f}#{parallel_count+1}" if parallel_count else f"{weight:.1f}"
        else:
            default_label = f"{weight:.1f}"

        self.edges[edge_id] = EdgeData(
            id=edge_id,
            source=source,
            target=target,
            weight=weight,
            label=default_label,
            color=color_rgb,
            directed=directed
        )
        
        self.update()
        return edge_id
    
    def remove_edge(self, edge_id: str):
        """Remove an edge"""
        if edge_id in self.edges:
            del self.edges[edge_id]
            self.selected_edges.discard(edge_id)
            self.update()
    
    def get_node_at(self, pos: QPointF) -> Optional[str]:
        """Get node at screen position"""
        world_pos = self.screen_to_world(pos)
        
        for node_id, node in self.nodes.items():
            node_screen = self.world_to_screen(node.pos)
            dx = pos.x() - node_screen.x()
            dy = pos.y() - node_screen.y()
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist <= node.size * self.zoom:
                return node_id
        
        return None
    
    def get_edge_at(self, pos: QPointF) -> Optional[str]:
        """Get edge at screen position"""
        threshold = 6.0

        # Preferencia y modo multigrafo para decidir si usamos selección curvada
        curved_enabled = self.settings.value('curved_multiedges', True, type=bool)
        allow_multigraph = False
        try:
            allow_multigraph = getattr(self.parent(), 'allow_multigraph', False)
        except Exception:
            pass

        best_id = None
        best_dist = float('inf')

        for edge_id, edge in self.edges.items():
            if edge.source not in self.nodes or edge.target not in self.nodes:
                continue
            
            source_node = self.nodes[edge.source]
            target_node = self.nodes[edge.target]
            
            p1 = self.world_to_screen(source_node.pos)
            p2 = self.world_to_screen(target_node.pos)

            if allow_multigraph and curved_enabled:
                # Usar misma lógica de curvatura que en el pintado
                info = getattr(self, '_edge_parallel_info', {})
                offset_index, count = info.get(edge_id, (0.0, 1))
                if count > 1:
                    cp = self._compute_control_point(p1, p2, offset_index)
                    # Muestrear la Bezier cuadrática y hallar mínima distancia
                    samples = 24
                    min_d = float('inf')
                    for s in range(samples + 1):
                        t = s / samples
                        q = self._quadratic_bezier_point(p1, cp, p2, t)
                        d = math.hypot(pos.x() - q.x(), pos.y() - q.y())
                        if d < min_d:
                            min_d = d
                    dist = min_d
                else:
                    # Caso no paralelo: usar distancia a segmento recto
                    dx = p2.x() - p1.x()
                    dy = p2.y() - p1.y()
                    length_sq = dx*dx + dy*dy
                    if length_sq == 0:
                        continue
                    t = max(0, min(1, ((pos.x() - p1.x()) * dx + (pos.y() - p1.y()) * dy) / length_sq))
                    proj_x = p1.x() + t * dx
                    proj_y = p1.y() + t * dy
                    dist = math.hypot(pos.x() - proj_x, pos.y() - proj_y)
            else:
                # Modo recto clásico
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                length_sq = dx*dx + dy*dy
                if length_sq == 0:
                    continue
                t = max(0, min(1, ((pos.x() - p1.x()) * dx + (pos.y() - p1.y()) * dy) / length_sq))
                proj_x = p1.x() + t * dx
                proj_y = p1.y() + t * dy
                dist = math.hypot(pos.x() - proj_x, pos.y() - proj_y)

            if dist < best_dist:
                best_dist = dist
                best_id = edge_id

        if best_id is not None and best_dist <= threshold:
            return best_id
        return None
    
    def clear_highlights(self):
        """Clear all highlights"""
        self.highlighted_nodes.clear()
        self.highlighted_edges.clear()
        self.update()
    
    def highlight_nodes(self, node_ids: List[str]):
        """Highlight specific nodes"""
        self.highlighted_nodes = set(node_ids)
        self.update()
    
    def highlight_edges(self, edge_ids: List[str]):
        """Highlight specific edges"""
        self.highlighted_edges = set(edge_ids)
        self.update()
    
    def clear_graph(self):
        """Clear all nodes and edges"""
        self.nodes.clear()
        self.edges.clear()
        self.selected_nodes.clear()
        self.selected_edges.clear()
        self.highlighted_nodes.clear()
        self.highlighted_edges.clear()
        self.node_counter = 0
        self.update()
    
    def auto_layout(self):
        """Automatically layout nodes using spring layout"""
        if not HAS_NETWORKX or not self.nodes:
            return
        
        G = nx.Graph()
        for node_id in self.nodes:
            G.add_node(node_id)
        for edge in self.edges.values():
            G.add_edge(edge.source, edge.target)
        
        try:
            pos = nx.spring_layout(G, k=2, iterations=50, scale=200)
            
            for node_id, (x, y) in pos.items():
                if node_id in self.nodes:
                    self.nodes[node_id].pos = (x, y)
            
            self.update()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error de layout",
                f"No se pudo aplicar el layout automático: {str(e)}"
            )
    
    def export_graphml(self, filename):
        """Export graph to GraphML format"""
        if not HAS_NETWORKX:
            return False
        
        G = nx.Graph()
        for node_id, node in self.nodes.items():
            G.add_node(node_id, label=node.label, x=node.pos[0], y=node.pos[1])
        for edge in self.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight, label=edge.label)
        
        nx.write_graphml(G, filename)
        return True
    
    def export_dot(self, filename):
        """Export graph to DOT format"""
        with open(filename, 'w') as f:
            f.write("graph G {\n")
            for node in self.nodes.values():
                f.write(f'  "{node.label}";\n')
            for edge in self.edges.values():
                src_label = self.nodes[edge.source].label
                tgt_label = self.nodes[edge.target].label
                f.write(f'  "{src_label}" -- "{tgt_label}" [label="{edge.weight:.1f}"];\n')
            f.write("}\n")
        return True
    
    def export_adjacency_matrix(self, filename):
        """Export graph as adjacency matrix"""
        node_list = list(self.nodes.keys())
        n = len(node_list)
        matrix = [[0.0] * n for _ in range(n)]
        
        for edge in self.edges.values():
            i = node_list.index(edge.source)
            j = node_list.index(edge.target)
            matrix[i][j] = edge.weight
            matrix[j][i] = edge.weight
        
        with open(filename, 'w') as f:
            # Write header
            f.write("," + ",".join(self.nodes[nid].label for nid in node_list) + "\n")
            # Write matrix
            for i, row in enumerate(matrix):
                f.write(self.nodes[node_list[i]].label + "," + ",".join(str(x) for x in row) + "\n")
        
        return True
    
    def export_edge_list(self, filename):
        """Export graph as edge list"""
        with open(filename, 'w') as f:
            f.write("source,target,weight\n")
            for edge in self.edges.values():
                src_label = self.nodes[edge.source].label
                tgt_label = self.nodes[edge.target].label
                f.write(f"{src_label},{tgt_label},{edge.weight}\n")
        return True

    # ========================================================================
    # PAINTING
    # ========================================================================
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        theme = self.settings.value('theme', 'Light')
        if theme == 'Dark':
            # Subtle vertical gradient for dark mode
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, QColor(24, 24, 24))
            grad.setColorAt(1, QColor(34, 34, 34))
            painter.fillRect(self.rect(), grad)
        else:
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, QColor(250, 250, 250))
            grad.setColorAt(1, QColor(235, 235, 235))
            painter.fillRect(self.rect(), grad)
        
        # Grid
        if self.show_grid:
            self.draw_grid(painter)
        
        # Edges
        # Preparar información de aristas paralelas (multigrafo) para dibujar con curvatura
        self._edge_parallel_info = {}
        try:
            allow_multigraph = getattr(self.parent(), 'allow_multigraph', False)
        except Exception:
            allow_multigraph = False
        curved_enabled = self.settings.value('curved_multiedges', True, type=bool)
        if allow_multigraph and curved_enabled and len(self.edges) > 0:
            groups = {}
            for eid, e in self.edges.items():
                # Agrupamos por par no ordenado para que ambas direcciones compartan la familia visual
                key = tuple(sorted((e.source, e.target)))
                groups.setdefault(key, []).append(eid)
            for key, eids in groups.items():
                # Orden determinista por id
                eids_sorted = sorted(eids)
                k = len(eids_sorted)
                if k <= 1:
                    self._edge_parallel_info[eids_sorted[0]] = (0.0, 1)
                else:
                    mid = (k - 1) / 2.0
                    for i, eid in enumerate(eids_sorted):
                        offset_index = i - mid  # valores simétricos [-m..0..+m]
                        self._edge_parallel_info[eid] = (offset_index, k)
        else:
            # Sin multigrafo, todas las aristas van rectas
            for eid in self.edges.keys():
                self._edge_parallel_info[eid] = (0.0, 1)

        for edge_id, edge in self.edges.items():
            self.draw_edge(
                painter,
                edge,
                edge_id in self.highlighted_edges,
                is_hovered=(edge_id == self.hovered_edge),
                is_selected=(edge_id in self.selected_edges)
            )
        
        # Nodes
        for node_id, node in self.nodes.items():
            is_highlighted = node_id in self.highlighted_nodes
            is_selected = node_id in self.selected_nodes
            is_hovered = node_id == self.hovered_node
            is_connect_source = node_id == self.connect_source
            
            self.draw_node(painter, node, is_highlighted, is_selected, is_hovered, is_connect_source)

        # Selection rectangle overlay
        if self.selection_box_active and self.selection_box_start and self.selection_box_current:
            rect = QRectF(self.selection_box_start, self.selection_box_current)
            pen = QPen(QColor(80,160,255,180), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(80,160,255,60)))
            painter.drawRect(rect.normalized())
    
    def draw_grid(self, painter: QPainter):
        """Draw grid"""
        theme = self.settings.value('theme', 'Light')
        # Ajuste de contraste para modo oscuro: líneas más sutiles pero visibles
        minor_color = QColor(31, 31, 31) if theme == 'Dark' else QColor(230, 230, 230)
        major_color = QColor(45, 45, 45) if theme == 'Dark' else QColor(210, 210, 210)
        painter.setPen(QPen(minor_color, 1))
        
        grid_spacing = self.grid_size * self.zoom
        
        # Vertical lines
        x = self.offset.x() % grid_spacing
        col = 0
        while x < self.width():
            # Major line every 5 cells
            if col % 5 == 0:
                painter.setPen(QPen(major_color, 1))
                painter.drawLine(int(x), 0, int(x), self.height())
                painter.setPen(QPen(minor_color, 1))
            else:
                painter.drawLine(int(x), 0, int(x), self.height())
            x += grid_spacing
            col += 1
        
        # Horizontal lines
        y = self.offset.y() % grid_spacing
        row = 0
        while y < self.height():
            if row % 5 == 0:
                painter.setPen(QPen(major_color, 1))
                painter.drawLine(0, int(y), self.width(), int(y))
                painter.setPen(QPen(minor_color, 1))
            else:
                painter.drawLine(0, int(y), self.width(), int(y))
            y += grid_spacing
            row += 1
    
    def draw_node(self, painter: QPainter, node: NodeData, highlighted: bool, selected: bool, hovered: bool, connect_source: bool):
        """Draw a node"""
        pos = self.world_to_screen(node.pos)
        radius = node.size * self.zoom
        
        # Shadow
        if not highlighted:
            shadow_offset = 2
            painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(pos, radius + shadow_offset, radius + shadow_offset)
        
        # Node color
        if highlighted:
            color = QColor(100, 255, 100)
        elif connect_source:
            color = QColor(255, 165, 0)
        elif selected:
            color = QColor(*node.color).lighter(120)
        elif hovered:
            color = QColor(*node.color).lighter(110)
        else:
            color = QColor(*node.color)

        # Gradient fill for nicer look
        grad = QLinearGradient(pos.x() - radius, pos.y() - radius, pos.x() + radius, pos.y() + radius)
        grad.setColorAt(0, color.lighter(120))
        grad.setColorAt(1, color.darker(120))
        painter.setBrush(QBrush(grad))
        
        # Border
        if selected or connect_source:
            painter.setPen(QPen(QColor(255, 200, 0), 3))
        else:
            theme = self.settings.value('theme', 'Light')
            if theme == 'Dark':
                painter.setPen(QPen(QColor(200, 200, 200), 2))
            else:
                painter.setPen(QPen(QColor(50, 50, 50), 2))
        
        painter.drawEllipse(pos, radius, radius)
        
        # Label
        if node.label:
            font_size = int(self.settings.value('font_size', 10))
            font = QFont('Arial', font_size, QFont.Bold)
            painter.setFont(font)
            
            theme = self.settings.value('theme', 'Light')
            if theme == 'Dark':
                painter.setPen(QPen(QColor(255, 255, 255)))
            else:
                painter.setPen(QPen(QColor(0, 0, 0)))
            
            painter.drawText(
                QRectF(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2),
                Qt.AlignCenter,
                node.label
            )
    
    def draw_edge(self, painter: QPainter, edge: EdgeData, highlighted: bool, is_hovered: bool=False, is_selected: bool=False):
        """Draw an edge"""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            return
        
        source_node = self.nodes[edge.source]
        target_node = self.nodes[edge.target]
        
        p1 = self.world_to_screen(source_node.pos)
        p2 = self.world_to_screen(target_node.pos)
        
        # Edge color
        if highlighted:
            color = QColor(255, 100, 100)
            width = 3
        elif is_selected or is_hovered:
            color = QColor(*edge.color).lighter(125)
            width = 3
        else:
            color = QColor(*edge.color)
            width = 2

        # Curvatura para aristas paralelas (multigrafo)
        offset_index, count = self._edge_parallel_info.get(edge.id, (0.0, 1))
        if count > 1:
            # Calcular punto de control desplazado perpendicularmente
            cp = self._compute_control_point(p1, p2, offset_index)
            path = QPainterPath(p1)
            path.quadTo(cp, p2)
            painter.setPen(QPen(color, width))
            painter.drawPath(path)
        else:
            painter.setPen(QPen(color, width))
            painter.drawLine(p1, p2)
        
        # Arrow for directed edges
        if edge.directed:
            # Pass target node size so arrow is placed at the node border
            target_node = self.nodes.get(edge.target)
            target_size = target_node.size if target_node is not None else 10
            if count > 1:
                self.draw_arrow_for_curve(painter, p1, cp, p2, color, target_size)
            else:
                self.draw_arrow(painter, p1, p2, color, target_size)
        
        # Weight label
        if edge.label:
            if count > 1:
                cp = self._compute_control_point(p1, p2, offset_index)
                mid_point = self._quadratic_bezier_point(p1, cp, p2, 0.5)
                mid_x, mid_y = mid_point.x(), mid_point.y()
            else:
                mid_x = (p1.x() + p2.x()) / 2
                mid_y = (p1.y() + p2.y()) / 2
            
            font_size = int(self.settings.value('font_size', 10))
            font = QFont('Arial', font_size - 1)
            painter.setFont(font)
            
            # Background for label
            theme = self.settings.value('theme', 'Light')
            bg = QColor(30,30,30) if theme == 'Dark' else QColor(255,255,255)
            fg = QColor(255,255,255) if theme == 'Dark' else QColor(0,0,0)
            painter.setPen(QPen(fg))

            # Rounded background
            text_rect = QRectF(mid_x - 18, mid_y - 10, 36, 20)
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(text_rect, 5, 5)
            painter.drawText(text_rect, Qt.AlignCenter, edge.label)
    
    def draw_arrow(self, painter: QPainter, p1: QPointF, p2: QPointF, color: QColor, target_size: float = 10):
        """Draw arrow head for directed edge"""
        arrow_size = 10
        
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
        
        # Normalize
        dx /= length
        dy /= length
        
        # Arrow position (at target node edge)
        # Use provided target_size (in unzoomed units) to offset arrow
        # NOTE: target_size will be multiplied by zoom to get screen-space radius
        arrow_pos = QPointF(
            p2.x() - dx * target_size * self.zoom,
            p2.y() - dy * target_size * self.zoom
        )
        
        # Arrow points
        angle = math.atan2(dy, dx)
        p_left = QPointF(
            arrow_pos.x() - arrow_size * math.cos(angle - math.pi/6),
            arrow_pos.y() - arrow_size * math.sin(angle - math.pi/6)
        )
        p_right = QPointF(
            arrow_pos.x() - arrow_size * math.cos(angle + math.pi/6),
            arrow_pos.y() - arrow_size * math.sin(angle + math.pi/6)
        )
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 2))
        poly = QPainterPath()
        poly.moveTo(arrow_pos)
        poly.lineTo(p_left)
        poly.lineTo(p_right)
        poly.closeSubpath()
        painter.drawPath(poly)

    def _compute_control_point(self, p1: QPointF, p2: QPointF, offset_index: float) -> QPointF:
        """Calcula el punto de control para una curva cuadrática entre p1 y p2 con un desplazamiento perpendicular.
        offset_index es un valor simétrico (p.ej. -1, 0, +1 o -0.5, +0.5) que escala la curvatura.
        """
        # Punto medio
        mx = (p1.x() + p2.x()) / 2.0
        my = (p1.y() + p2.y()) / 2.0
        # Vector de p1 a p2
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist == 0:
            return QPointF(mx, my)
        # Vector normal perpendicular
        nx = -dy / dist
        ny = dx / dist
        # Magnitud base de curvatura proporcional a la distancia y al zoom
        base = 0.18 * dist  # 18% de la longitud
        offset = base * offset_index
        return QPointF(mx + nx * offset, my + ny * offset)

    def _quadratic_bezier_point(self, p0: QPointF, p1: QPointF, p2: QPointF, t: float) -> QPointF:
        """Punto en una curva Bezier cuadrática para parámetro t."""
        x = (1 - t) * (1 - t) * p0.x() + 2 * (1 - t) * t * p1.x() + t * t * p2.x()
        y = (1 - t) * (1 - t) * p0.y() + 2 * (1 - t) * t * p1.y() + t * t * p2.y()
        return QPointF(x, y)

    def draw_arrow_for_curve(self, painter: QPainter, p1: QPointF, cp: QPointF, p2: QPointF, color: QColor, target_size: float = 10):
        """Dibuja la flecha al final de una curva cuadrática usando la tangente en t=1 (vector 2*(p2-cp))."""
        # Tangente en t=1 para Bezier cuadrática
        dx = (p2.x() - cp.x()) * 2.0
        dy = (p2.y() - cp.y()) * 2.0
        length = math.hypot(dx, dy)
        if length == 0:
            # Fallback a línea recta
            return self.draw_arrow(painter, p1, p2, color, target_size)
        dx /= length
        dy /= length

        arrow_pos = QPointF(
            p2.x() - dx * target_size * self.zoom,
            p2.y() - dy * target_size * self.zoom
        )
        arrow_size = 10
        angle = math.atan2(dy, dx)
        p_left = QPointF(
            arrow_pos.x() - arrow_size * math.cos(angle - math.pi/6),
            arrow_pos.y() - arrow_size * math.sin(angle - math.pi/6)
        )
        p_right = QPointF(
            arrow_pos.x() - arrow_size * math.cos(angle + math.pi/6),
            arrow_pos.y() - arrow_size * math.sin(angle + math.pi/6)
        )
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 2))
        poly = QPainterPath()
        poly.moveTo(arrow_pos)
        poly.lineTo(p_left)
        poly.lineTo(p_right)
        poly.closeSubpath()
        painter.drawPath(poly)
    
    # ========================================================================
    # MOUSE EVENTS
    # ========================================================================
    
    def mousePressEvent(self, event: QMouseEvent):
        pos = event.pos()
        
        if event.button() == Qt.LeftButton:
            node_id = self.get_node_at(pos)
            edge_id = None if node_id else self.get_edge_at(pos)

            if self.mode == 'select':
                if node_id:
                    # Selección de nodo (multi con Ctrl)
                    # Si no está seleccionado y no hay Ctrl, limpiar selecciones previas
                    if not (event.modifiers() & Qt.ControlModifier):
                        if node_id not in self.selected_nodes:
                            self.selected_nodes.clear()
                            self.selected_edges.clear()
                    if event.modifiers() & Qt.ControlModifier and node_id in self.selected_nodes:
                        self.selected_nodes.discard(node_id)
                    else:
                        # Si el nodo no estaba seleccionado, añadirlo (permitir arrastrar único)
                        self.selected_nodes.add(node_id)

                    # Iniciar arrastre del nodo (o del grupo seleccionado)
                    self.dragging_node = node_id
                    self.drag_start = QPointF(pos)
                    self.dragging_initiated = False
                    # Preparar posiciones originales para arrastre grupal
                    # Aseguramos que al menos el nodo clicado está en el diccionario
                    self.group_drag_orig_positions = {nid: tuple(self.nodes[nid].pos) for nid in self.selected_nodes}
                    # Cambiar cursor para indicar arrastre
                    self.setCursor(Qt.ClosedHandCursor)
                    # Pausar animación si está corriendo para evitar conflicto de posiciones
                    try:
                        if getattr(self, 'animation_controller', None) and self.animation_controller.is_running():
                            self.animation_controller.pause()
                    except Exception:
                        pass
                    self.node_selected.emit(node_id)
                elif edge_id:
                    if not (event.modifiers() & Qt.ControlModifier):
                        if edge_id not in self.selected_edges:
                            self.selected_nodes.clear()
                            self.selected_edges.clear()
                    if event.modifiers() & Qt.ControlModifier and edge_id in self.selected_edges:
                        self.selected_edges.discard(edge_id)
                    else:
                        self.selected_edges.add(edge_id)
                    self.edge_selected.emit(edge_id)
                else:
                    # Espacio vacío: NO crear nodo para evitar clics accidentales
                    # Opción de pan con Alt + clic izquierdo
                    if event.modifiers() & Qt.AltModifier:
                        self.panning = True
                        self.pan_start = pos
                        self.setCursor(Qt.ClosedHandCursor)
                    else:
                        if not (event.modifiers() & Qt.ControlModifier):
                            self.selected_nodes.clear()
                            self.selected_edges.clear()

            elif self.mode == 'connect':
                if node_id:
                    if self.connect_source is None:
                        self.connect_source = node_id
                    else:
                        if self.connect_source != node_id:
                            self.add_edge(self.connect_source, node_id)
                        self.connect_source = None

            self.update()
        
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start = pos
            self.setCursor(Qt.ClosedHandCursor)
        
        elif event.button() == Qt.RightButton:
            self.show_context_menu(pos)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()
        
        # Update hover state
        self.hovered_node = self.get_node_at(pos)
        self.hovered_edge = self.get_edge_at(pos) if not self.hovered_node else None
        
        # Arrastre de nodo o grupo de nodos
        if self.dragging_node and self.drag_start:
            dist = (pos - self.drag_start).manhattanLength()
            if not self.dragging_initiated and dist >= self.drag_threshold:
                # Marcar inicio de arrastre y guardar el estado PREVIO para permitir "undo" del movimiento
                self.dragging_initiated = True
                try:
                    parent = self.parent()
                    if parent and hasattr(parent, 'save_state'):
                        parent.save_state()
                except Exception:
                    pass
                # asegurar cursor de arrastre
                self.setCursor(Qt.ClosedHandCursor)
            if self.dragging_initiated:
                delta_screen = pos - self.drag_start
                delta_world = QPointF(delta_screen.x() / self.zoom, delta_screen.y() / self.zoom)
                # Bloqueo de eje opcional con Shift: solo mueve en el eje de mayor desplazamiento
                if event.modifiers() & Qt.ShiftModifier:
                    if abs(delta_world.x()) >= abs(delta_world.y()):
                        delta_world.setY(0)
                    else:
                        delta_world.setX(0)
                # Mover todos los nodos seleccionados usando posiciones originales
                for nid, orig_pos in self.group_drag_orig_positions.items():
                    new_pos = (orig_pos[0] + delta_world.x(), orig_pos[1] + delta_world.y())
                    if self.snap_to_grid:
                        p = self.snap_to_grid_pos(QPointF(*new_pos))
                        new_pos = (p.x(), p.y())
                    self.nodes[nid].pos = new_pos
                self.update()
        
        # Si no estamos arrastrando pero estamos sobre un nodo, mostrar cursor de mano
        elif not self.panning:
            if self.hovered_node:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        # Panning
        elif self.panning and self.pan_start:
            delta = pos - self.pan_start
            self.offset += delta
            self.pan_start = pos
        
        self.update()
        # Update status bar coordinates in parent
        try:
            if hasattr(self.parent(), 'on_canvas_mouse_move'):
                world = self.screen_to_world(pos)
                self.parent().on_canvas_mouse_move(world)
        except Exception:
            pass
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # Antes de limpiar, determinar si hubo movimiento para guardar estado (undo)
            moved = False
            if self.dragging_initiated and self.group_drag_orig_positions:
                for nid, orig_pos in self.group_drag_orig_positions.items():
                    new_pos = self.nodes[nid].pos
                    if (abs(new_pos[0] - orig_pos[0]) > 0.0001) or (abs(new_pos[1] - orig_pos[1]) > 0.0001):
                        moved = True
                        break
            self.dragging_node = None
            self.drag_start = None
            self.dragging_initiated = False
            self.group_drag_orig_positions.clear()
            # Restaurar cursor
            self.setCursor(Qt.ArrowCursor)
            # Guardar estado si hubo movimiento (usar parent MainWindow)
            if moved:
                parent = self.parent()
                if parent and hasattr(parent, 'save_state'):
                    parent.save_state()
        
        elif event.button() == Qt.MiddleButton:
            self.panning = False
            self.pan_start = None
            self.setCursor(Qt.ArrowCursor)

    def selectAll(self):
        """Select all nodes and edges"""
        self.selected_nodes = set(self.nodes.keys())
        self.selected_edges = set(self.edges.keys())
        self.update()
    
    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel"""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        
        # Zoom centered on mouse position
        old_zoom = self.zoom
        self.zoom *= zoom_factor
        self.zoom = max(0.1, min(5.0, self.zoom))
        
        # Adjust offset to keep mouse position fixed
        mouse_pos = event.pos()
        self.offset = mouse_pos - (mouse_pos - self.offset) * (self.zoom / old_zoom)
        
        self.update()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Delete selected nodes and edges
            for node_id in list(self.selected_nodes):
                self.remove_node(node_id)
            for edge_id in list(self.selected_edges):
                self.remove_edge(edge_id)
            
            self.selected_nodes.clear()
            self.selected_edges.clear()
            self.update()
        elif event.key() == Qt.Key_A and (event.modifiers() & Qt.ControlModifier):
            # Select all
            self.selected_nodes = set(self.nodes.keys())
            self.selected_edges = set(self.edges.keys())
            self.update()
        elif event.key() == Qt.Key_Plus and (event.modifiers() & Qt.ControlModifier):
            # Zoom in
            self.zoom *= 1.1
            self.zoom = min(5.0, self.zoom)
            self.update()
        elif event.key() == Qt.Key_Minus and (event.modifiers() & Qt.ControlModifier):
            # Zoom out
            self.zoom *= 0.9
            self.zoom = max(0.1, self.zoom)
            self.update()
        elif event.key() == Qt.Key_0 and (event.modifiers() & Qt.ControlModifier):
            # Reset zoom
            self.zoom = 1.0
            self.offset = QPointF(0, 0)
            self.update()
        elif event.key() == Qt.Key_F5:
            self.parent().run_bfs()
        elif event.key() == Qt.Key_F6:
            self.parent().run_dfs()
        elif event.key() == Qt.Key_F7:
            self.parent().run_dijkstra()
        elif event.key() == Qt.Key_F8:
            self.parent().run_kruskal()
    
    def show_context_menu(self, pos: QPointF):
        """Show context menu"""
        from PyQt5.QtWidgets import QMenu

        node_id = self.get_node_at(pos)
        edge_id = self.get_edge_at(pos)

        menu = QMenu(self)

        if node_id:
            node = self.nodes[node_id]
            rename_act = menu.addAction("Renombrar nodo…")
            size_act = menu.addAction("Cambiar tamaño…")
            color_act = menu.addAction("Cambiar color…")
            duplicate_act = menu.addAction("Duplicar nodo")
            connect_act = menu.addAction("Conectar con otro seleccionado")
            center_act = menu.addAction("Centrar vista")
            menu.addSeparator()
            delete_act = menu.addAction("Eliminar nodo")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == rename_act:
                text, ok = QInputDialog.getText(self, "Renombrar nodo", "Nuevo nombre:", text=node.label)
                if ok and text.strip():
                    if any(n.label == text.strip() and n.id != node_id for n in self.nodes.values()):
                        QMessageBox.warning(self, "Etiqueta duplicada", "Ya existe otro nodo con esa etiqueta.")
                    else:
                        node.label = text.strip(); self.update()
            elif action == size_act:
                val, ok = QInputDialog.getDouble(self, "Tamaño de nodo", "Nuevo tamaño:", value=node.size, min=5.0, max=100.0, decimals=1)
                if ok:
                    node.size = val; self.update()
            elif action == color_act:
                c = QColorDialog.getColor(QColor(*node.color), self, "Color de nodo")
                if c.isValid():
                    node.color = c.getRgb()[:3]; self.update()
            elif action == duplicate_act:
                new_pos = (node.pos[0] + 20, node.pos[1] + 20)
                self.add_node(new_pos, label=f"{node.label}_copy")
            elif action == connect_act:
                others = [n for n in self.selected_nodes if n != node_id]
                if others:
                    target = others[0]
                    self.add_edge(node_id, target)
                else:
                    QMessageBox.information(self, "Conectar", "Seleccione otro nodo adicional para conectar.")
            elif action == center_act:
                node_screen = self.world_to_screen(node.pos)
                center_screen = QPointF(self.width()/2, self.height()/2)
                delta = center_screen - node_screen
                self.offset += delta; self.update()
            elif action == delete_act:
                self.remove_node(node_id)
        elif edge_id:
            edge = self.edges[edge_id]
            weight_act = menu.addAction("Editar peso…")
            color_act = menu.addAction("Cambiar color…")
            toggle_dir_act = menu.addAction("Invertir / Alternar dirección")
            menu.addSeparator()
            delete_act = menu.addAction("Eliminar arista")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == weight_act:
                val, ok = QInputDialog.getDouble(self, "Peso de arista", "Nuevo peso:", value=edge.weight, min=0.1, max=1000.0, decimals=2)
                if ok:
                    edge.weight = val; edge.label = f"{val:.2f}"; self.update()
            elif action == color_act:
                c = QColorDialog.getColor(QColor(*edge.color), self, "Color de arista")
                if c.isValid():
                    edge.color = c.getRgb()[:3]; self.update()
            elif action == toggle_dir_act:
                if edge.directed:
                    edge.source, edge.target = edge.target, edge.source
                else:
                    edge.directed = True
                self.update()
            elif action == delete_act:
                self.remove_edge(edge_id)
        else:
            add_node_act = menu.addAction("Añadir nodo aquí")
            select_all_act = menu.addAction("Seleccionar todo")
            invert_sel_act = menu.addAction("Invertir selección")
            clear_highlight_act = menu.addAction("Limpiar resaltado")
            layout_act = menu.addAction("Layout automático")
            copy_img_act = menu.addAction("Copiar imagen")
            menu.addSeparator()
            new_graph_act = menu.addAction("Nuevo grafo")
            prefs_act = menu.addAction("Preferencias…")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == add_node_act:
                world = self.screen_to_world(pos)
                self.add_node((world.x(), world.y()))
            elif action == select_all_act:
                self.selectAll()
            elif action == invert_sel_act:
                all_nodes = set(self.nodes.keys())
                self.selected_nodes = all_nodes - self.selected_nodes
                self.update()
            elif action == clear_highlight_act:
                self.clear_highlights()
            elif action == layout_act:
                self.auto_layout()
            elif action == copy_img_act:
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setPixmap(self.grab())
            elif action == new_graph_act:
                mw = self.window(); hasattr(mw, 'new_graph') and mw.new_graph()
            elif action == prefs_act:
                mw = self.window(); hasattr(mw, 'show_preferences') and mw.show_preferences()

        self.update()


# ============================================================================
# MAIN WINDOW
# ============================================================================

# ==========================================================================
# Collapsible Section (accordion-like) helper
# ==========================================================================
class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent=None, collapsed: bool = False):
        super().__init__(parent)
        self._header = QToolButton(self)
        self._header.setText(title)
        self._header.setCheckable(True)
        self._header.setChecked(not collapsed)
        self._header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._header.setArrowType(Qt.DownArrow if not collapsed else Qt.RightArrow)
        self._header.clicked.connect(self._on_toggled)
        self._content = QWidget(self)
        self._content.setVisible(not collapsed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._header)
        lay.addWidget(self._content)

    def setContentLayout(self, layout: QLayout):
        self._content.setLayout(layout)

    def _on_toggled(self, checked: bool):
        self._content.setVisible(checked)
        self._header.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def setCollapsed(self, collapsed: bool):
        self._header.setChecked(not collapsed)
        self._on_toggled(not collapsed)

    def isCollapsed(self) -> bool:
        return not self._header.isChecked()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grafos - Graphic User Interface")
        self.setGeometry(100, 100, 1200, 800)
        # Asegura que nunca tenga una altura mínima mayor que la pantalla
        self.setMinimumSize(QSize(800, 540))
        
        self.settings = QSettings('GraphGUI', 'Preferences')
        # Pasamos self como parent para permitir acceso a flags globales y save_state desde el canvas
        self.canvas = GraphCanvas(self)
        self.current_file_path: Optional[str] = None
        
        # History for undo/redo (debe inicializarse antes de init_ui si allí se llama save_state)
        self.history = []
        self.history_index = -1
        self.max_history = 50

        # Flags de proyecto
        self.graph_directed = self.settings.value('graph_directed', False, type=bool)
        self.allow_multigraph = self.settings.value('allow_multigraph', False, type=bool)
        self.animate_algorithms = self.settings.value('animate_algorithms', True, type=bool)

    # Historiales
        self.log_history = []  # type: List[str]
        self.algorithm_history = []  # type: List[Dict[str, str]]

        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """Initialize UI"""
        # Central widget
        self.setCentralWidget(self.canvas)
        
        # Create menus
        self.create_menus()
        
        # Create toolbar
        self.create_toolbar()

        # Create secondary toolbar (view/theme)
        self.create_view_toolbar()

        # Create floating quick actions bar
        self.create_quick_actions()
        
        # Create dock widgets
        self.create_docks()
        
        # Status bar
        self.create_status_bar()

        # Global shortcuts (additional)
        self.register_shortcuts()

    # ------------------------------------------------------------------
    # Animation / Mode controls
    # ------------------------------------------------------------------
    def toggle_animation(self):
        """Toggle between start and pause for the animation controller"""
        try:
            ac = self.canvas.animation_controller
            if ac.is_running():
                ac.pause()
                self.play_pause_action.setChecked(False)
                # cambiar icono a Play
                try:
                    self.play_pause_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                except Exception:
                    pass
                self.log("Animación pausada")
            else:
                ac.start()
                self.play_pause_action.setChecked(True)
                try:
                    self.play_pause_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                except Exception:
                    pass
                self.log("Animación iniciada")
        except Exception:
            self.log("Control de animación no disponible")

    def stop_animation(self):
        """Stop the animation and clear highlights"""
        try:
            ac = self.canvas.animation_controller
            ac.stop()
            # uncheck play button
            try:
                self.play_pause_action.setChecked(False)
            except Exception:
                pass
            # limpiar resaltados
            self.canvas.clear_highlights()
            self.log("Animación detenida")
        except Exception:
            self.log("No se pudo detener la animación")

    def cancel_mode(self):
        """Cancel any active edit/connection mode and return to select mode"""
        try:
            # Use set_mode to ensure UI/state updated
            self.set_mode('select')
            # Uncheck toolbar toggles if present
            try:
                self.select_action.setChecked(True)
                self.connect_action.setChecked(False)
            except Exception:
                pass
            self.log("Modo cancelado: volver a Seleccionar")
            self.canvas.update()
        except Exception:
            self.log("No se pudo cancelar el modo")

    def show_algorithm_summary(self, name: str, success: bool, brief: str, details: str = None):
        """Show a summary alert after running an algorithm.

        - name: algorithm name
        - success: True if completed OK, False if error/partial
        - brief: short one-line summary
        - details: longer text with steps, path or error message
        """
        # Registrar en historial de algoritmos
        try:
            self.algorithm_history.append({
                'algorithm': name,
                'success': '1' if success else '0',
                'summary': brief,
                'details': details or ''
            })
        except Exception:
            pass
        try:
            if success:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle(f"{name} - Completado")
                msg.setText(brief)
                if details:
                    msg.setDetailedText(details)
                msg.exec_()
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle(f"{name} - Error / Incompleto")
                msg.setText(brief)
                if details:
                    msg.setDetailedText(details)
                msg.exec_()
        except Exception:
            # Fallback simple message
            if success:
                QMessageBox.information(self, f"{name}", brief)
            else:
                QMessageBox.warning(self, f"{name}", brief)

        # Save initial state
        self.save_state()
    
    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        self.file_menu = menubar.addMenu("Archivo")
        
        new_action = QAction("Nuevo", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_graph)
        self.file_menu.addAction(new_action)
        
        open_action = QAction("Abrir...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_graph)
        self.file_menu.addAction(open_action)

        # Recent files submenu
        self.recent_menu = QMenu("Recientes", self)
        self.file_menu.addMenu(self.recent_menu)
        self.rebuild_recent_files_menu()
        
        save_action = QAction("Guardar", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_graph)
        self.file_menu.addAction(save_action)

        save_as_action = QAction("Guardar como...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_graph_as)
        self.file_menu.addAction(save_as_action)
        
        self.file_menu.addSeparator()
        
        export_menu = self.file_menu.addMenu("Exportar")
        
        export_png_action = QAction("PNG...", self)
        export_png_action.triggered.connect(self.export_png)
        export_menu.addAction(export_png_action)
        
        export_graphml_action = QAction("GraphML...", self)
        export_graphml_action.triggered.connect(self.export_graphml)
        export_menu.addAction(export_graphml_action)
        
        export_dot_action = QAction("DOT...", self)
        export_dot_action.triggered.connect(self.export_dot)
        export_menu.addAction(export_dot_action)
        
        export_matrix_action = QAction("Matriz de Adyacencia (CSV)...", self)
        export_matrix_action.triggered.connect(self.export_adjacency_matrix)
        export_menu.addAction(export_matrix_action)
        
        export_edges_action = QAction("Lista de Aristas (CSV)...", self)
        export_edges_action.triggered.connect(self.export_edge_list)
        export_menu.addAction(export_edges_action)
        
        # Export SVG
        export_svg_action = QAction("SVG...", self)
        export_svg_action.triggered.connect(self.export_svg)
        export_menu.addAction(export_svg_action)

        # Export PDF
        export_pdf_action = QAction("PDF...", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        export_menu.addAction(export_pdf_action)

        self.file_menu.addSeparator()
        
        preferences_action = QAction("Preferencias...", self)
        preferences_action.triggered.connect(self.show_preferences)
        self.file_menu.addAction(preferences_action)
        
        self.file_menu.addSeparator()
        
        exit_action = QAction("Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        # Exportaciones adicionales de historial (al final del menú Archivo para fácil acceso)
        export_results_action = QAction("Exportar Resultados Algoritmos (CSV)", self)
        export_results_action.triggered.connect(self.export_algorithm_results)
        self.file_menu.addAction(export_results_action)
        export_log_action = QAction("Exportar Log", self)
        export_log_action.triggered.connect(self.export_log)
        self.file_menu.addAction(export_log_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Editar")

        undo_action = QAction("Deshacer", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        # guardar referencia para habilitar/deshabilitar
        self.undo_menu_action = undo_action
        
        redo_action = QAction("Rehacer", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        self.redo_menu_action = redo_action
        
        edit_menu.addSeparator()
        
        clear_action = QAction("Limpiar grafo", self)
        clear_action.triggered.connect(self.clear_graph)
        edit_menu.addAction(clear_action)

        edit_menu.addSeparator()
        
        select_all_action = QAction("Seleccionar todo", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.canvas.selectAll)
        edit_menu.addAction(select_all_action)

        invert_sel_action = QAction("Invertir selección", self)
        invert_sel_action.setShortcut("Ctrl+I")
        invert_sel_action.triggered.connect(self.invert_selection)
        edit_menu.addAction(invert_sel_action)

        connect_sel_action = QAction("Conectar seleccionados", self)
        connect_sel_action.setShortcut("Ctrl+E")
        connect_sel_action.triggered.connect(self.connect_selected_nodes)
        edit_menu.addAction(connect_sel_action)

        copy_img_action = QAction("Copiar imagen del canvas", self)
        copy_img_action.setShortcut("Ctrl+Alt+C")
        copy_img_action.triggered.connect(self.copy_canvas_image)
        edit_menu.addAction(copy_img_action)
        
        algo_menu = menubar.addMenu("Algoritmos")
        
        # Traversal algorithms
        traversal_menu = algo_menu.addMenu("Recorrido")
        
        bfs_action = QAction("BFS - Búsqueda en anchura", self)
        bfs_action.setShortcut("F5")
        bfs_action.triggered.connect(self.run_bfs)
        traversal_menu.addAction(bfs_action)
        
        dfs_action = QAction("DFS - Búsqueda en profundidad", self)
        dfs_action.setShortcut("F6")
        dfs_action.triggered.connect(self.run_dfs)
        traversal_menu.addAction(dfs_action)
        
        # Shortest path algorithms
        path_menu = algo_menu.addMenu("Camino Más Corto")
        
        dijkstra_action = QAction("Dijkstra", self)
        dijkstra_action.setShortcut("F7")
        dijkstra_action.triggered.connect(self.run_dijkstra)
        path_menu.addAction(dijkstra_action)
        
        bellman_ford_action = QAction("Bellman-Ford", self)
        bellman_ford_action.triggered.connect(self.run_bellman_ford)
        path_menu.addAction(bellman_ford_action)
        
        floyd_warshall_action = QAction("Floyd-Warshall (Todos los pares)", self)
        floyd_warshall_action.triggered.connect(self.run_floyd_warshall)
        path_menu.addAction(floyd_warshall_action)
        
        astar_action = QAction("A* (con heurística euclidiana)", self)
        astar_action.triggered.connect(self.run_astar)
        path_menu.addAction(astar_action)

        # Nuevo: diálogo unificado de caminos y camino más largo (DAG)
        paths_dialog_action = QAction("Caminos (corto/largo)...", self)
        paths_dialog_action.triggered.connect(self.run_paths_dialog)
        path_menu.addAction(paths_dialog_action)

        longest_path_action = QAction("Camino más largo (DAG)", self)
        longest_path_action.triggered.connect(self.run_longest_path)
        path_menu.addAction(longest_path_action)
        
        # MST algorithms
        mst_menu = algo_menu.addMenu("Árbol de Expansión Mínima")
        
        kruskal_action = QAction("Kruskal", self)
        kruskal_action.setShortcut("F8")
        kruskal_action.triggered.connect(self.run_kruskal)
        mst_menu.addAction(kruskal_action)
        
        prim_action = QAction("Prim", self)
        prim_action.triggered.connect(self.run_prim)
        mst_menu.addAction(prim_action)
        
        # Other algorithms
        algo_menu.addSeparator()
        
        topo_sort_action = QAction("Ordenamiento Topológico", self)
        topo_sort_action.triggered.connect(self.run_topological_sort)
        algo_menu.addAction(topo_sort_action)
        
        scc_action = QAction("Componentes Fuertemente Conexas (Tarjan)", self)
        scc_action.triggered.connect(self.run_tarjan_scc)
        algo_menu.addAction(scc_action)
        
        algo_menu.addSeparator()
        
        clear_highlight_action = QAction("Limpiar resaltado", self)
        clear_highlight_action.triggered.connect(self.canvas.clear_highlights)
        algo_menu.addAction(clear_highlight_action)

        # Componentes conexas rápido
        comp_action = QAction("Componentes Conexas (resaltar)", self)
        comp_action.triggered.connect(self.highlight_connected_components)
        algo_menu.addAction(comp_action)

        # ================= NUEVAS FAMILIAS DE ALGORITMOS =================
        algo_menu.addSeparator()
        flow_menu = algo_menu.addMenu("Flujo / Corte")
        maxflow_action = QAction("Máximo Flujo (Edmonds-Karp)", self)
        maxflow_action.triggered.connect(self.run_max_flow)
        flow_menu.addAction(maxflow_action)
        # Futuro: Dinic

        cycles_action = QAction("Detectar Ciclos", self)
        cycles_action.triggered.connect(self.run_cycle_detection)
        algo_menu.addAction(cycles_action)

        coloring_action = QAction("Coloreo (Welsh-Powell)", self)
        coloring_action.triggered.connect(self.run_graph_coloring)
        algo_menu.addAction(coloring_action)

        communities_action = QAction("Comunidades (Girvan-Newman)", self)
        communities_action.triggered.connect(self.run_communities)
        algo_menu.addAction(communities_action)

        bipartite_action = QAction("Verificar Bipartito", self)
        bipartite_action.triggered.connect(self.run_bipartite_check)
        algo_menu.addAction(bipartite_action)

        matching_action = QAction("Matching Máximo", self)
        matching_action.triggered.connect(self.run_maximum_matching)
        algo_menu.addAction(matching_action)
        # Nuevos algoritmos agregados
        euler_action = QAction("Euleriano (Hierholzer)", self)
        euler_action.triggered.connect(self.run_eulerian)
        algo_menu.addAction(euler_action)
        planar_action = QAction("Planaridad", self)
        planar_action.triggered.connect(self.check_planarity)
        algo_menu.addAction(planar_action)
        tree_action = QAction("Validar Árbol", self)
        tree_action.triggered.connect(self.check_tree)
        algo_menu.addAction(tree_action)
        export_results_algo_action = QAction("Exportar resultados (CSV)", self)
        export_results_algo_action.triggered.connect(self.export_algorithm_results)
        algo_menu.addAction(export_results_algo_action)
        
        tools_menu = menubar.addMenu("Herramientas")
        
        generator_action = QAction("Generador de Grafos...", self)
        generator_action.triggered.connect(self.show_graph_generator)
        tools_menu.addAction(generator_action)
        
        analysis_action = QAction("Análisis de Grafo...", self)
        analysis_action.triggered.connect(self.show_graph_analysis)
        tools_menu.addAction(analysis_action)
        
        tools_menu.addSeparator()
        
        color_by_degree_action = QAction("Colorear por Grado", self)
        color_by_degree_action.triggered.connect(self.color_by_degree)
        tools_menu.addAction(color_by_degree_action)
        
        color_by_centrality_action = QAction("Colorear por Centralidad", self)
        color_by_centrality_action.triggered.connect(self.color_by_centrality)
        tools_menu.addAction(color_by_centrality_action)

        tools_menu.addSeparator()
        # Toggles de proyecto
        toggle_directed = QAction("Grafo dirigido (global)", self)
        toggle_directed.setCheckable(True)
        toggle_directed.setChecked(self.graph_directed)
        def on_toggle_directed(ch: bool):
            self.graph_directed = ch
            self.settings.setValue('graph_directed', ch)
            self.log(f"Modo grafo dirigido: {'Sí' if ch else 'No'}")
        toggle_directed.triggered.connect(on_toggle_directed)
        tools_menu.addAction(toggle_directed)

        toggle_multigraph = QAction("Permitir multigrafo", self)
        toggle_multigraph.setCheckable(True)
        toggle_multigraph.setChecked(self.allow_multigraph)
        def on_toggle_multigraph(ch: bool):
            self.allow_multigraph = ch
            self.settings.setValue('allow_multigraph', ch)
            self.log(f"Multigrafo permitido: {'Sí' if ch else 'No'}")
        toggle_multigraph.triggered.connect(on_toggle_multigraph)
        tools_menu.addAction(toggle_multigraph)

        toggle_animation = QAction("Animar algoritmos (paso a paso)", self)
        toggle_animation.setCheckable(True)
        toggle_animation.setChecked(self.animate_algorithms)
        def on_toggle_animation(ch: bool):
            self.animate_algorithms = ch
            self.settings.setValue('animate_algorithms', ch)
            self.log(f"Animación de algoritmos: {'Activada' if ch else 'Desactivada'}")
        toggle_animation.triggered.connect(on_toggle_animation)
        tools_menu.addAction(toggle_animation)
        
        # View menu (guardar referencia para añadir toggles de docks más tarde)
        self.view_menu = menubar.addMenu("Vista")
        
        view_3d_action = QAction("Visualización 3D", self)
        view_3d_action.triggered.connect(self.show_3d_view)
        self.view_menu.addAction(view_3d_action)
        
        self.view_menu.addSeparator()
        
        auto_layout_action = QAction("Layout automático", self)
        auto_layout_action.triggered.connect(self.canvas.auto_layout)
        self.view_menu.addAction(auto_layout_action)
        
        self.view_menu.addSeparator()
        
        grid_action = QAction("Mostrar rejilla", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(self.canvas.show_grid)
        grid_action.triggered.connect(self.toggle_grid)
        self.view_menu.addAction(grid_action)
        
        snap_action = QAction("Ajustar a rejilla", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(self.canvas.snap_to_grid)
        snap_action.triggered.connect(self.toggle_snap)
        self.view_menu.addAction(snap_action)

        self.view_menu.addSeparator()

        dark_toggle_action = QAction("Tema oscuro", self)
        dark_toggle_action.setCheckable(True)
        dark_toggle_action.setChecked(self.settings.value('theme','Light') == 'Dark')
        dark_toggle_action.setShortcut("Ctrl+Shift+D")
        dark_toggle_action.triggered.connect(lambda checked: self.set_theme_checked(checked))
        self.view_menu.addAction(dark_toggle_action)
        
        help_menu = menubar.addMenu("Ayuda")
        
        shortcuts_action = QAction("Atajos de Teclado", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    # ============================
    # Recent files helpers
    # ============================
    def add_recent_file(self, path: str):
        settings = QSettings('GraphGUI', 'Preferences')
        recent = settings.value('recent_files', [], type=list)
        # Ensure list of strings
        if not isinstance(recent, list):
            recent = []
        # Remove if exists and insert at top
        recent = [p for p in recent if p != path]
        recent.insert(0, path)
        # Limit to 5
        recent = recent[:5]
        settings.setValue('recent_files', recent)
        self.rebuild_recent_files_menu()

    def rebuild_recent_files_menu(self):
        if not hasattr(self, 'recent_menu'):
            return
        self.recent_menu.clear()
        settings = QSettings('GraphGUI', 'Preferences')
        recent = settings.value('recent_files', [], type=list)
        if not recent:
            dummy = QAction("(Vacío)", self)
            dummy.setEnabled(False)
            self.recent_menu.addAction(dummy)
            return
        for path in recent:
            act = QAction(path, self)
            act.triggered.connect(lambda checked=False, p=path: self.open_recent_file(p))
            self.recent_menu.addAction(act)

    def open_recent_file(self, path: str):
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'nodes' not in data or 'edges' not in data:
                raise ValueError("Formato de archivo inválido")
            self.canvas.clear_graph()
            node_labels = []
            for node_data in data['nodes']:
                node = NodeData.from_dict(node_data)
                self.canvas.nodes[node.id] = node
                node_labels.append(node.label)
            for edge_data in data['edges']:
                edge = EdgeData.from_dict(edge_data)
                if edge.source in self.canvas.nodes and edge.target in self.canvas.nodes:
                    self.canvas.edges[edge.id] = edge
            max_node_num = 0
            for label in node_labels:
                if label.startswith('N') and label[1:].isdigit():
                    num = int(label[1:])
                    if num > max_node_num:
                        max_node_num = num
            self.canvas.node_counter = max_node_num
            self.canvas.update()
            self.save_state()
            self.log(f"Grafo cargado: {path}")
            self.current_file_path = path
            self.add_recent_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el grafo:\n{str(e)}")
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Herramientas")
        self.addToolBar(toolbar)
        toolbar.setMovable(True)
        # Establecer tamaño de iconos (usa QSize importado de QtCore)
        toolbar.setIconSize(QSize(16,16))
        
        # Mode selection (sin seleccionar ninguno por defecto)
        self.select_action = QAction("Seleccionar", self)
        self.select_action.setCheckable(True)
        self.select_action.setChecked(False)
        self.select_action.triggered.connect(lambda: self._on_mode_click('select'))
        toolbar.addAction(self.select_action)

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setCheckable(True)
        self.connect_action.setChecked(False)
        self.connect_action.triggered.connect(lambda: self._on_mode_click('connect'))
        toolbar.addAction(self.connect_action)
        
        toolbar.addSeparator()
        
        # Quick actions
        auto_layout_btn = QAction("Layout Auto", self)
        auto_layout_btn.triggered.connect(self.canvas.auto_layout)
        toolbar.addAction(auto_layout_btn)
        
        view_3d_btn = QAction("Vista 3D", self)
        view_3d_btn.triggered.connect(self.show_3d_view)
        toolbar.addAction(view_3d_btn)

        # Theme toggle
        theme_toggle = QAction("🌗 Tema", self)
        theme_toggle.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_toggle)

        # Separator and undo/redo quick icons
        toolbar.addSeparator()
        undo_icon = self.style().standardIcon(QStyle.SP_ArrowBack)
        redo_icon = self.style().standardIcon(QStyle.SP_ArrowForward)
        undo_btn = QAction(undo_icon, "Deshacer", self)
        undo_btn.triggered.connect(self.undo)
        redo_btn = QAction(redo_icon, "Rehacer", self)
        redo_btn.triggered.connect(self.redo)
        toolbar.addAction(undo_btn)
        toolbar.addAction(redo_btn)
        # Control de animación: iniciar/pausar y detener
        play_icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        pause_icon = self.style().standardIcon(QStyle.SP_MediaPause)
        stop_icon = self.style().standardIcon(QStyle.SP_MediaStop)
        self.play_pause_action = QAction(play_icon, "Iniciar/Pausar animación", self)
        self.play_pause_action.setCheckable(True)
        self.play_pause_action.triggered.connect(self.toggle_animation)
        stop_action = QAction(stop_icon, "Detener animación", self)
        stop_action.triggered.connect(self.stop_animation)
        toolbar.addAction(self.play_pause_action)
        toolbar.addAction(stop_action)
        # referencias para controlar enabled
        self.undo_toolbar_action = undo_btn
        self.redo_toolbar_action = redo_btn
        # Inicializa estado
        if hasattr(self, 'update_undo_redo_actions'):
            self.update_undo_redo_actions()

        # Botón para cancelar modo activo (connect/añadir)
        cancel_mode_act = QAction("Cancelar modo", self)
        cancel_mode_act.triggered.connect(self.cancel_mode)
        toolbar.addAction(cancel_mode_act)

    def _on_mode_click(self, mode: str):
        """Gestiona selección visual de modo, permitiendo estado 'ninguno' al inicio."""
        if mode == 'select':
            self.select_action.setChecked(True)
            self.connect_action.setChecked(False)
        elif mode == 'connect':
            self.select_action.setChecked(False)
            self.connect_action.setChecked(True)
        self.set_mode(mode)

    def create_view_toolbar(self):
        """Secondary toolbar for view controls"""
        view_toolbar = QToolBar("Vista")
        self.addToolBar(Qt.BottomToolBarArea, view_toolbar)
        view_toolbar.setMovable(True)
        zoom_in = QAction("Zoom +", self)
        zoom_in.setShortcut("Ctrl++")
        zoom_in.triggered.connect(lambda: self.adjust_zoom(1.1))
        zoom_out = QAction("Zoom -", self)
        zoom_out.setShortcut("Ctrl+-")
        zoom_out.triggered.connect(lambda: self.adjust_zoom(0.9))
        zoom_reset = QAction("Reset Zoom", self)
        zoom_reset.setShortcut("Ctrl+0")
        zoom_reset.triggered.connect(lambda: self.reset_zoom())
        view_toolbar.addAction(zoom_in)
        view_toolbar.addAction(zoom_out)
        view_toolbar.addAction(zoom_reset)
        view_toolbar.addSeparator()
        grid_toggle = QAction("Rejilla", self)
        grid_toggle.setCheckable(True)
        grid_toggle.setChecked(self.canvas.show_grid)
        grid_toggle.triggered.connect(lambda checked: self.toggle_grid(checked))
        snap_toggle = QAction("Snap", self)
        snap_toggle.setCheckable(True)
        snap_toggle.setChecked(self.canvas.snap_to_grid)
        snap_toggle.triggered.connect(lambda checked: self.toggle_snap(checked))
        view_toolbar.addAction(grid_toggle)
        view_toolbar.addAction(snap_toggle)
        # Toggle rápido del panel de Log (expandir/ocultar)
        log_toggle = QAction("Log ⌄/⌃", self)
        log_toggle.triggered.connect(self.toggle_log)
        view_toolbar.addSeparator()
        view_toolbar.addAction(log_toggle)

    def create_quick_actions(self):
        """Floating widget with quick add buttons"""
        dock = QDockWidget("Acciones rápidas", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        panel = QWidget()
        lay = QVBoxLayout(panel)
        add_node_btn = QPushButton("➕ Nodo")
        add_node_btn.setToolTip("Añadir nodo al centro (Ctrl+Shift+N)")
        add_node_btn.clicked.connect(self.add_center_node)
        lay.addWidget(add_node_btn)
        add_edge_btn = QPushButton("🔗 Arista")
        add_edge_btn.setToolTip("Modo conectar (Ctrl+Shift+E)")
        add_edge_btn.clicked.connect(lambda: self.set_mode('connect'))
        lay.addWidget(add_edge_btn)
        clear_highlight_btn = QPushButton("💡 Limpiar resaltado")
        clear_highlight_btn.clicked.connect(self.canvas.clear_highlights)
        lay.addWidget(clear_highlight_btn)
        lay.addStretch()
        panel.setLayout(lay)
        dock.setWidget(panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def create_status_bar(self):
        sb = self.statusBar()
        sb.showMessage("Listo")
        self.coord_label = QLabel("x: 0.0, y: 0.0")
        sb.addPermanentWidget(self.coord_label)
        self.zoom_label = QLabel("Zoom: 100%")
        sb.addPermanentWidget(self.zoom_label)
        self.sel_label = QLabel("Sel: 0 nodos, 0 aristas")
        sb.addPermanentWidget(self.sel_label)
        self.mode_label = QLabel("Modo: seleccionar")
        sb.addPermanentWidget(self.mode_label)
        self.theme_label = QLabel(f"Tema: {self.settings.value('theme','Light')}")
        sb.addPermanentWidget(self.theme_label)

    def on_canvas_mouse_move(self, world_pos: QPointF):
        self.coord_label.setText(f"x: {world_pos.x():.1f}, y: {world_pos.y():.1f}")

    def register_shortcuts(self):
        # Extra shortcuts not in menus
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, activated=self.add_center_node)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, activated=lambda: self.set_mode('connect'))
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_graph)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, activated=self.toggle_theme)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search_input.setFocus())
        QShortcut(QKeySequence("Ctrl+Shift+L"), self, activated=self.canvas.auto_layout)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self.canvas.clear_highlights)
        # Tutorial y exportaciones
        QShortcut(QKeySequence("F1"), self, activated=self.show_tutorial)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, activated=self.export_algorithm_results)
        QShortcut(QKeySequence("Ctrl+Alt+L"), self, activated=self.export_log)

    def show_tutorial(self):
        """Muestra un tutorial rápido con atajos y funciones básicas."""
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Tutorial rápido")
            dlg.setModal(True)
            layout = QVBoxLayout(dlg)

            intro = QLabel(
                """
                <h3>Bienvenido a la Interfaz de Grafos</h3>
                <p>Estos son algunos pasos y atajos útiles para empezar:</p>
                <ul>
                  <li><b>Nuevo/Abrir/Guardar</b>: Archivo → Nuevo/Abrir/Guardar</li>
                  <li><b>Añadir nodo</b>: Ctrl+Shift+N o botón "➕ Nodo" en Acciones rápidas</li>
                  <li><b>Conectar nodos</b>: Ctrl+Shift+E para entrar al modo conectar y luego clic en dos nodos</li>
                  <li><b>Auto-layout</b>: Ctrl+Shift+L</li>
                  <li><b>Limpiar resaltado</b>: Ctrl+Shift+C</li>
                  <li><b>Zoom</b>: Ctrl++ / Ctrl+- / Ctrl+0</li>
                  <li><b>Exportar</b>: Archivo → Exportar (PNG, PDF, GraphML, DOT, CSV)</li>
                  <li><b>Exportar resultados</b>: Ctrl+Shift+R</li>
                  <li><b>Exportar log</b>: Ctrl+Alt+L</li>
                  <li><b>Algoritmos</b>: Menú Algoritmos (BFS, DFS, Dijkstra, Flujo, Euleriano, Planaridad, Árbol, etc.)</li>
                </ul>
                """
            )
            intro.setWordWrap(True)
            intro.setTextFormat(Qt.RichText)
            layout.addWidget(intro)

            btns = QHBoxLayout()
            btn_ok = QPushButton("Cerrar")
            btn_ok.clicked.connect(dlg.accept)
            btns.addStretch(1)
            btns.addWidget(btn_ok)
            layout.addLayout(btns)

            dlg.resize(560, 420)
            dlg.exec_()
            self.log("Se mostró el tutorial rápido")
        except Exception as e:
            QMessageBox.information(self, "Tutorial", "Consulta el menú Ayuda o los atajos para comenzar.")
            self.log(f"Error al mostrar tutorial: {e}")

    def add_center_node(self):
        center = self.canvas.screen_to_world(QPointF(self.canvas.width()/2, self.canvas.height()/2))
        nid = self.canvas.add_node((center.x(), center.y()))
        if nid:
            self.save_state()
            self.log("Nodo agregado en el centro")

    def adjust_zoom(self, factor):
        old = self.canvas.zoom
        self.canvas.zoom = max(0.1, min(5.0, self.canvas.zoom * factor))
        self.canvas.update()
        self.zoom_label.setText(f"Zoom: {int(self.canvas.zoom*100)}%")
        self.log(f"Zoom {old:.2f} -> {self.canvas.zoom:.2f}")

    def reset_zoom(self):
        self.canvas.zoom = 1.0
        self.canvas.offset = QPointF(0,0)
        self.canvas.update()
        self.zoom_label.setText("Zoom: 100%")
        self.log("Zoom restablecido")

    def toggle_theme(self):
        current = self.settings.value('theme','Light')
        new = 'Dark' if current != 'Dark' else 'Light'
        self.settings.setValue('theme', new)
        self.apply_theme()
        self.theme_label.setText(f"Tema: {new}")
        self.log(f"Tema cambiado a {new}")
    
    def create_docks(self):
        """Create dock widgets"""
        # Info dock
        info_dock = QDockWidget("Información", self)
        info_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        info_widget = QWidget()

        # Node list
        self.node_list = QListWidget()
        self.node_list.itemDoubleClicked.connect(self.select_node_from_list)

        # Edge list
        self.edge_list = QListWidget()
        self.edge_list.itemDoubleClicked.connect(self.select_edge_from_list)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Etiqueta o ID...")
        self.search_input.returnPressed.connect(self.search_node)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self.search_node)

        # Construir secciones colapsables en cascada
        info_sections_layout = QVBoxLayout()
        info_sections_layout.setContentsMargins(0, 0, 0, 0)
        info_sections_layout.setSpacing(6)

        # Controles expandir/contraer
        info_ctrl = QHBoxLayout(); info_ctrl.setContentsMargins(6, 4, 6, 0); info_ctrl.setSpacing(8)
        btn_expand_all = QToolButton(); btn_expand_all.setText("Expandir todo")
        btn_collapse_all = QToolButton(); btn_collapse_all.setText("Contraer todo")
        info_ctrl.addWidget(btn_expand_all); info_ctrl.addWidget(btn_collapse_all); info_ctrl.addStretch(1)
        info_sections_layout.addLayout(info_ctrl)

        # Estados persistentes
        nodes_open = self.settings.value('ui/info/nodes_open', True, type=bool)
        edges_open = self.settings.value('ui/info/edges_open', True, type=bool)
        search_open = self.settings.value('ui/info/search_open', False, type=bool)

        # Sección: Nodos
        nodes_sec = CollapsibleSection("Nodos", info_widget, collapsed=not nodes_open)
        nodes_lay = QVBoxLayout(); nodes_lay.setContentsMargins(8, 2, 8, 8)
        nodes_lay.addWidget(self.node_list)
        nodes_sec.setContentLayout(nodes_lay)
        info_sections_layout.addWidget(nodes_sec)

        # Sección: Aristas
        edges_sec = CollapsibleSection("Aristas", info_widget, collapsed=not edges_open)
        edges_lay = QVBoxLayout(); edges_lay.setContentsMargins(8, 2, 8, 8)
        edges_lay.addWidget(self.edge_list)
        edges_sec.setContentLayout(edges_lay)
        info_sections_layout.addWidget(edges_sec)

        # Sección: Buscar
        search_sec = CollapsibleSection("Buscar", info_widget, collapsed=not search_open)
        search_lay = QVBoxLayout(); search_lay.setContentsMargins(8, 2, 8, 8)
        search_lay.addWidget(self.search_input)
        search_lay.addWidget(search_btn)
        search_sec.setContentLayout(search_lay)
        info_sections_layout.addWidget(search_sec)
        info_sections_layout.addStretch(1)

        # Conexiones de persistencia y acciones globales
        nodes_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/info/nodes_open', c))
        edges_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/info/edges_open', c))
        search_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/info/search_open', c))
        btn_expand_all.clicked.connect(lambda: [s.setCollapsed(False) for s in (nodes_sec, edges_sec, search_sec)])
        btn_collapse_all.clicked.connect(lambda: [s.setCollapsed(True) for s in (nodes_sec, edges_sec, search_sec)])

        info_widget.setLayout(info_sections_layout)
        info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, info_dock)

        # Log dock
        log_dock = QDockWidget("Log", self)
        log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Mantener mínima baja para no elevar la altura mínima de la ventana
        self.log_text.setMinimumHeight(50)
        log_dock.setWidget(self.log_text)

        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        # Fijar el dock en el fondo (no movible/float/close), pero redimensionable por splitter
        log_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        log_dock.setMinimumHeight(70)
        # Guardar referencia y crear acción de alternar visibilidad
        self.log_dock = log_dock
        log_toggle_action = self.log_dock.toggleViewAction()
        log_toggle_action.setText("Panel Log")
        log_toggle_action.setShortcut("F9")
        # Ajustar altura inicial (recupera última preferencia)
        initial_h = int(self.settings.value('log_height', 160))
        try:
            self.resizeDocks([self.log_dock], [max(100, initial_h)], Qt.Vertical)
        except Exception:
            pass
        # Añadir al menú Vista si está listo
        if hasattr(self, 'view_menu') and self.view_menu is not None:
            self.view_menu.addSeparator()
            self.view_menu.addAction(log_toggle_action)

        # Update lists timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_lists)
        self.update_timer.start(500)

        # Properties dock (nuevo)
        prop_dock = QDockWidget("Propiedades", self)
        prop_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        prop_widget = QWidget()
        prop_layout = QVBoxLayout()
        prop_layout.setContentsMargins(0, 0, 0, 0)
        prop_layout.setSpacing(6)

        # Barra expandir/contraer
        prop_ctrl = QHBoxLayout(); prop_ctrl.setContentsMargins(6, 4, 6, 0); prop_ctrl.setSpacing(8)
        p_expand_all = QToolButton(); p_expand_all.setText("Expandir todo")
        p_collapse_all = QToolButton(); p_collapse_all.setText("Contraer todo")
        prop_ctrl.addWidget(p_expand_all); prop_ctrl.addWidget(p_collapse_all); prop_ctrl.addStretch(1)
        prop_layout.addLayout(prop_ctrl)

        # Selector de tipo
        self.prop_type_combo = QComboBox()
        self.prop_type_combo.addItems(["Nodo", "Arista"])

        # Sección General (persistencia)
        general_open = self.settings.value('ui/props/general_open', True, type=bool)
        node_open = self.settings.value('ui/props/node_open', True, type=bool)
        edge_open = self.settings.value('ui/props/edge_open', False, type=bool)

        general_sec = CollapsibleSection("General", prop_widget, collapsed=not general_open)
        general_lay = QVBoxLayout(); general_lay.setContentsMargins(8, 2, 8, 8)
        general_lay.addWidget(self.prop_type_combo)
        self.prop_id_label = QLabel("ID: -")
        general_lay.addWidget(self.prop_id_label)
        general_sec.setContentLayout(general_lay)
        prop_layout.addWidget(general_sec)

        # Nodo campos
        self.node_label_edit = QLineEdit()
        self.node_size_spin = QDoubleSpinBox(); self.node_size_spin.setRange(5.0, 200.0)
        self.node_color_btn = QPushButton("Color nodo")
        self.node_color_btn.clicked.connect(self._change_selected_node_color)
        nodo_sec = CollapsibleSection("Nodo", prop_widget, collapsed=not node_open)
        nodo_lay = QVBoxLayout(); nodo_lay.setContentsMargins(8, 2, 8, 8)
        nodo_lay.addWidget(QLabel("Etiqueta nodo:"))
        nodo_lay.addWidget(self.node_label_edit)
        nodo_lay.addWidget(QLabel("Tamaño nodo:"))
        nodo_lay.addWidget(self.node_size_spin)
        nodo_lay.addWidget(self.node_color_btn)
        nodo_sec.setContentLayout(nodo_lay)
        prop_layout.addWidget(nodo_sec)

        # Arista campos
        self.edge_label_edit = QLineEdit()
        self.edge_weight_spin = QDoubleSpinBox(); self.edge_weight_spin.setRange(0.1, 10000.0); self.edge_weight_spin.setDecimals(2)
        self.edge_directed_check = QCheckBox("Dirigida")
        self.edge_color_btn = QPushButton("Color arista")
        self.edge_color_btn.clicked.connect(self._change_selected_edge_color)
        arista_sec = CollapsibleSection("Arista", prop_widget, collapsed=not edge_open)
        arista_lay = QVBoxLayout(); arista_lay.setContentsMargins(8, 2, 8, 8)
        arista_lay.addWidget(QLabel("Etiqueta arista:"))
        arista_lay.addWidget(self.edge_label_edit)
        arista_lay.addWidget(QLabel("Peso arista:"))
        arista_lay.addWidget(self.edge_weight_spin)
        arista_lay.addWidget(self.edge_directed_check)
        arista_lay.addWidget(self.edge_color_btn)
        arista_sec.setContentLayout(arista_lay)
        prop_layout.addWidget(arista_sec)

        # Botones aplicar
        apply_btn = QPushButton("Aplicar cambios")
        apply_btn.clicked.connect(self.apply_properties_changes)
        prop_layout.addWidget(apply_btn)
        prop_layout.addStretch(1)
        prop_widget.setLayout(prop_layout)
        prop_dock.setWidget(prop_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, prop_dock)
        self.properties_dock = prop_dock

        # Persistencia y acciones globales
        general_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/props/general_open', c))
        nodo_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/props/node_open', c))
        arista_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/props/edge_open', c))
        p_expand_all.clicked.connect(lambda: [s.setCollapsed(False) for s in (general_sec, nodo_sec, arista_sec)])
        p_collapse_all.clicked.connect(lambda: [s.setCollapsed(True) for s in (general_sec, nodo_sec, arista_sec)])

        # Animation control dock (simple)
        anim_dock = QDockWidget("Animación", self)
        anim_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        anim_widget = QWidget()
        anim_layout = QVBoxLayout(anim_widget)
        a_ctrl = QHBoxLayout(); a_ctrl.setContentsMargins(6, 4, 6, 0); a_ctrl.setSpacing(8)
        a_expand_all = QToolButton(); a_expand_all.setText("Expandir todo")
        a_collapse_all = QToolButton(); a_collapse_all.setText("Contraer todo")
        a_ctrl.addWidget(a_expand_all); a_ctrl.addWidget(a_collapse_all); a_ctrl.addStretch(1)
        anim_layout.addLayout(a_ctrl)
        self.anim_play_btn = QPushButton("▶ Reproducir")    
        self.anim_play_btn.clicked.connect(lambda: self.canvas.animation_controller.start())
        self.anim_stop_btn = QPushButton("⏹ Detener")
        self.anim_stop_btn.clicked.connect(lambda: self.canvas.animation_controller.stop())
        self.anim_step_btn = QPushButton("⏭ Paso")
        self.anim_step_btn.clicked.connect(lambda: self.canvas.animation_controller.next_step())
        speed_label = QLabel("Velocidad (ms):")
        self.anim_speed_spin = QSpinBox(); self.anim_speed_spin.setRange(50, 5000); self.anim_speed_spin.setValue(1000)
        self.anim_speed_spin.valueChanged.connect(lambda v: self.canvas.animation_controller.set_speed(v))
        # Sección Controles
        controls_open = self.settings.value('ui/anim/controls_open', True, type=bool)
        controls_sec = CollapsibleSection("Controles", anim_widget, collapsed=not controls_open)
        controls_lay = QVBoxLayout(); controls_lay.setContentsMargins(8, 2, 8, 8)
        controls_lay.addWidget(self.anim_play_btn)
        controls_lay.addWidget(self.anim_stop_btn)
        controls_lay.addWidget(self.anim_step_btn)
        controls_lay.addWidget(speed_label)
        controls_lay.addWidget(self.anim_speed_spin)
        controls_sec.setContentLayout(controls_lay)
        anim_layout.addWidget(controls_sec)
        anim_layout.addStretch(1)
        anim_widget.setLayout(anim_layout)
        anim_dock.setWidget(anim_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, anim_dock)
        self.animation_dock = anim_dock
        controls_sec._header.clicked.connect(lambda c: self.settings.setValue('ui/anim/controls_open', c))
        a_expand_all.clicked.connect(lambda: controls_sec.setCollapsed(False))
        a_collapse_all.clicked.connect(lambda: controls_sec.setCollapsed(True))

    def load_properties(self, tipo: str, obj_id: str):
        """Carga datos en panel propiedades según selección"""
        self.prop_type_combo.setCurrentText(tipo)
        self.prop_id_label.setText(f"ID: {obj_id[:8]}")
        if tipo == 'Nodo' and obj_id in self.canvas.nodes:
            node = self.canvas.nodes[obj_id]
            self.node_label_edit.setText(node.label)
            self.node_size_spin.setValue(node.size)
            self.node_color_btn.setStyleSheet(f"background-color: rgb({node.color[0]}, {node.color[1]}, {node.color[2]});")
        elif tipo == 'Arista' and obj_id in self.canvas.edges:
            edge = self.canvas.edges[obj_id]
            self.edge_label_edit.setText(edge.label)
            self.edge_weight_spin.setValue(edge.weight)
            self.edge_directed_check.setChecked(edge.directed)
            self.edge_color_btn.setStyleSheet(f"background-color: rgb({edge.color[0]}, {edge.color[1]}, {edge.color[2]});")

    # ------------------------------------------------------------------
    # Dock title click-to-collapse helper
    # ------------------------------------------------------------------
    def _make_dock_collapsible(self, dock: QDockWidget, settings_key: str):
        """Convierte un QDockWidget en colapsable al picar el título.
        Guarda/restaura altura con QSettings usando settings_key.
        """
        # Título personalizado con flecha
        bar = QWidget()
        bar.setObjectName("DockTitleBar")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(8, 2, 8, 2)
        hbox.setSpacing(6)
        arrow = QLabel("▾", bar)
        title_lbl = QLabel(dock.windowTitle(), bar)
        title_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        hbox.addWidget(arrow)
        hbox.addWidget(title_lbl)
        hbox.addStretch(1)
        bar.setCursor(Qt.PointingHandCursor)

        def refresh_title(text=None):
            title_lbl.setText(dock.windowTitle())

        try:
            dock.windowTitleChanged.connect(refresh_title)
        except Exception:
            pass

        def toggle():
            collapsed = getattr(dock, '_collapsed', False)
            if not collapsed:
                # Guardar altura actual y ocultar contenido
                try:
                    self.settings.setValue(settings_key, max(120, dock.height()))
                except Exception:
                    pass
                if dock.widget():
                    dock.widget().setVisible(False)
                dock._collapsed = True
                arrow.setText('▸')
                try:
                    self.resizeDocks([dock], [bar.sizeHint().height() + 6], Qt.Vertical)
                except Exception:
                    dock.setMaximumHeight(bar.sizeHint().height() + 6)
            else:
                # Mostrar contenido y restaurar altura
                if dock.widget():
                    dock.widget().setVisible(True)
                dock._collapsed = False
                arrow.setText('▾')
                h = int(self.settings.value(settings_key, 240))
                try:
                    self.resizeDocks([dock], [max(150, h)], Qt.Vertical)
                except Exception:
                    dock.setMaximumHeight(16777215)  # reset

        # Manejar click
        def bar_mouse_press(event):
            toggle()
            QWidget.mousePressEvent(bar, event)

        bar.mousePressEvent = bar_mouse_press
        dock.setTitleBarWidget(bar)
        dock._collapsed = False

    def apply_properties_changes(self):
        tipo = self.prop_type_combo.currentText()
        # Buscar elemento seleccionado actual
        if tipo == 'Nodo' and self.canvas.selected_nodes:
            # Edita el primero
            nid = next(iter(self.canvas.selected_nodes))
            node = self.canvas.nodes.get(nid)
            if node:
                nuevo_label = self.node_label_edit.text().strip()
                if nuevo_label and any(n.label == nuevo_label and n.id != nid for n in self.canvas.nodes.values()):
                    QMessageBox.warning(self, "Etiqueta duplicada", "Ya existe otro nodo con esa etiqueta.")
                else:
                    node.label = nuevo_label
                node.size = self.node_size_spin.value()
                self.canvas.update()
                self.save_state()
                self.log(f"Nodo actualizado: {node.label}")
        elif tipo == 'Arista' and self.canvas.selected_edges:
            eid = next(iter(self.canvas.selected_edges))
            edge = self.canvas.edges.get(eid)
            if edge:
                edge.label = self.edge_label_edit.text().strip()
                nuevo_peso = self.edge_weight_spin.value()
                if nuevo_peso <= 0:
                    QMessageBox.warning(self, "Peso inválido", "El peso debe ser > 0.")
                else:
                    edge.weight = nuevo_peso
                edge.directed = self.edge_directed_check.isChecked()
                self.canvas.update()
                self.save_state()
                self.log("Arista actualizada")

    def _change_selected_node_color(self):
        if self.canvas.selected_nodes:
            nid = next(iter(self.canvas.selected_nodes))
            node = self.canvas.nodes.get(nid)
            if node:
                color = QColorDialog.getColor(QColor(*node.color), self)
                if color.isValid():
                    node.color = color.getRgb()[:3]
                    self.node_color_btn.setStyleSheet(f"background-color: {color.name()};")
                    self.canvas.update(); self.save_state(); self.log("Color de nodo cambiado")

    def _change_selected_edge_color(self):
        if self.canvas.selected_edges:
            eid = next(iter(self.canvas.selected_edges))
            edge = self.canvas.edges.get(eid)
            if edge:
                color = QColorDialog.getColor(QColor(*edge.color), self)
                if color.isValid():
                    edge.color = color.getRgb()[:3]
                    self.edge_color_btn.setStyleSheet(f"background-color: {color.name()};")
                    self.canvas.update(); self.save_state(); self.log("Color de arista cambiado")
    
    def set_mode(self, mode: str):
        """Set interaction mode"""
        self.canvas.mode = mode
        self.canvas.connect_source = None
        self.canvas.update()
        self.log(f"Modo: {mode}")
        if hasattr(self, 'mode_label'):
            self.mode_label.setText(f"Modo: {mode}")
    
    def apply_theme(self):
        """Apply theme from settings (modern dark/light with good contrast)."""
        theme = self.settings.value('theme', 'Dark')

        # Usa Fusion como base para uniformidad
        try:
            QApplication.setStyle('Fusion')
        except Exception:
            pass

        app = QApplication.instance()

        if theme == 'Dark':
            # Paleta oscura con contraste cuidado
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(18, 18, 18))
            palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
            palette.setColor(QPalette.Base, QColor(26, 26, 26))
            palette.setColor(QPalette.AlternateBase, QColor(33, 33, 33))
            palette.setColor(QPalette.ToolTipBase, QColor(35, 35, 35))
            palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
            palette.setColor(QPalette.Text, QColor(224, 224, 224))
            palette.setColor(QPalette.Button, QColor(33, 33, 33))
            palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
            palette.setColor(QPalette.BrightText, QColor(255, 85, 85))
            palette.setColor(QPalette.Link, QColor(100, 180, 255))
            palette.setColor(QPalette.Highlight, QColor(62, 115, 255))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor(130, 130, 130))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(130, 130, 130))
            if app:
                app.setPalette(palette)
            else:
                self.setPalette(palette)

            # Hoja de estilos para uniformar controles
            dark_qss = """
            QMainWindow, QDialog, QWidget {
                background-color: #121212;
                color: #E0E0E0;
            }

            /* Menús y barra de menú */
            QMenuBar { background-color: #1A1A1A; }
            QMenuBar::item { background: transparent; padding: 4px 10px; }
            QMenuBar::item:selected { background: #2A2A2A; }
            QMenu { background-color: #1E1E1E; border: 1px solid #2A2A2A; }
            QMenu::item:selected { background: #2C3E70; }

            /* Toolbars y status bar */
            QToolBar { background: #1A1A1A; border: none; spacing: 6px; }
            QStatusBar { background: #1A1A1A; color: #BEBEBE; }

            /* Docks */
            QDockWidget::title {
                background: #1A1A1A; padding: 6px 8px; color: #BBBBBB; border-bottom: 1px solid #2A2A2A;
            }

            /* Entradas de texto y editores */
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #1E1E1E; color: #E0E0E0; border: 1px solid #2E2E2E; border-radius: 4px; padding: 4px 6px;
                selection-background-color: #3E73FF; selection-color: #FFFFFF;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #3A6CF0; }
            QComboBox QAbstractItemView { background: #1E1E1E; border: 1px solid #2E2E2E; selection-background-color: #2C3E70; selection-color: #FFFFFF; }

            /* Botones */
            QPushButton {
                background-color: #2A2A2A; color: #EAEAEA; border: 1px solid #3A3A3A; border-radius: 4px; padding: 6px 10px;
            }
            QPushButton:hover { background-color: #333333; border-color: #4A4A4A; }
            QPushButton:pressed { background-color: #2C3E70; border-color: #2C3E70; }
            QPushButton:disabled { color: #888888; background: #222222; border-color: #2E2E2E; }

            /* Listas, árboles y tablas */
            QListWidget, QTreeWidget, QTableWidget, QTableView {
                background: #1A1A1A; color: #E0E0E0; alternate-background-color: #171717; gridline-color: #2A2A2A;
                selection-background-color: #2C3E70; selection-color: #FFFFFF; border: 1px solid #2A2A2A; border-radius: 4px;
            }
            QHeaderView::section { background: #1E1E1E; color: #CFCFCF; border: 1px solid #2A2A2A; padding: 4px 6px; }

            /* Tabs */
            QTabWidget::pane { border-top: 1px solid #2A2A2A; }
            QTabBar::tab { background: #1A1A1A; color: #CFCFCF; border: 1px solid #2A2A2A; border-bottom-color: #2A2A2A; padding: 6px 10px; margin-right: 1px; }
            QTabBar::tab:selected { background: #222222; color: #FFFFFF; }
            QTabBar::tab:hover { background: #232323; }

            /* Checks, radios y sliders */
            QCheckBox, QRadioButton { spacing: 6px; }
            QSlider::groove:horizontal { height: 6px; background: #252525; border-radius: 3px; }
            QSlider::handle:horizontal { background: #4E8CFF; width: 14px; margin: -4px 0; border-radius: 7px; }

            /* Tooltips */
            QToolTip { background-color: #232323; color: #E0E0E0; border: 1px solid #2E2E2E; }

            /* GroupBox */
            QGroupBox { border: 1px solid #2A2A2A; border-radius: 6px; margin-top: 12px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; color: #BBBBBB; }
            """
            if app:
                app.setStyleSheet(dark_qss)
            else:
                self.setStyleSheet(dark_qss)
        else:
            # Tema claro por defecto del sistema
            if app:
                app.setPalette(QApplication.style().standardPalette())
                app.setStyleSheet("")
            else:
                self.setPalette(QApplication.style().standardPalette())
                self.setStyleSheet("")

        # Refrescar canvas por cambio de colores de rejilla, etc.
        self.canvas.update()
    
    def update_lists(self):
        """Update node and edge lists"""
        # Update node list
        self.node_list.clear()
        node_ids_in_order = list(self.canvas.nodes.keys())
        for node_id in node_ids_in_order:
            node = self.canvas.nodes[node_id]
            item = QListWidgetItem(f"{node.label} ({node.id[:8]})")
            item.setData(Qt.UserRole, node.id) # Store node ID for selection
            self.node_list.addItem(item)
        
        # Update edge list
        self.edge_list.clear()
        edge_ids_in_order = list(self.canvas.edges.keys())
        for edge_id in edge_ids_in_order:
            edge = self.canvas.edges[edge_id]
            source_label = self.canvas.nodes[edge.source].label
            target_label = self.canvas.nodes[edge.target].label
            arrow = "→" if edge.directed else "↔"
            item = QListWidgetItem(f"{source_label} {arrow} {target_label} (w={edge.weight:.1f})")
            item.setData(Qt.UserRole, edge.id) # Store edge ID for selection
            self.edge_list.addItem(item)
        # Update selection counts in status bar
        if hasattr(self, 'sel_label'):
            self.sel_label.setText(f"Sel: {len(self.canvas.selected_nodes)} nodos, {len(self.canvas.selected_edges)} aristas")

    def invert_selection(self):
        """Invertir selección de nodos y aristas"""
        all_nodes = set(self.canvas.nodes.keys())
        all_edges = set(self.canvas.edges.keys())
        self.canvas.selected_nodes = all_nodes - self.canvas.selected_nodes
        self.canvas.selected_edges = all_edges - self.canvas.selected_edges
        self.canvas.update()
        self.update_lists()
        self.log("Selección invertida")

    def connect_selected_nodes(self):
        """Conecta dos nodos seleccionados"""
        if len(self.canvas.selected_nodes) != 2:
            QMessageBox.information(self, "Conectar", "Seleccione exactamente dos nodos.")
            return
        a, b = list(self.canvas.selected_nodes)
        eid = self.canvas.add_edge(a, b)
        if eid:
            self.save_state()
            self.log("Arista creada entre seleccionados")

    def copy_canvas_image(self):
        """Copia imagen del canvas al portapapeles"""
        if not self.canvas.nodes:
            QMessageBox.information(self, "Copiar imagen", "No hay nada que copiar.")
            return
        pixmap = self.canvas.grab()
        QApplication.clipboard().setPixmap(pixmap)
        self.log("Imagen copiada al portapapeles")
    
    def log(self, message: str):
        """Add message to log"""
        self.log_text.append(message)
        self.statusBar().showMessage(message)
        try:
            self.log_history.append(message)
        except Exception:
            pass

    # ================= EXPORTACIÓN DE LOG Y RESULTADOS =================
    def export_log(self):
        if not self.log_history:
            QMessageBox.information(self, "Exportar Log", "No hay entradas en el log.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Log", "", "Text (*.txt);;CSV (*.csv)")
        if not filename:
            return
        try:
            if filename.lower().endswith('.csv'):
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['linea'])
                    for line in self.log_history:
                        writer.writerow([line])
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    for line in self.log_history:
                        f.write(line + '\n')
            self.log(f"Log exportado: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar log: {e}")

    def export_algorithm_results(self):
        if not self.algorithm_history:
            QMessageBox.information(self, "Resultados", "No hay resultados de algoritmos todavía.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Resultados Algoritmos", "", "CSV (*.csv)")
        if not filename:
            return
        try:
            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['algorithm','success','summary','details'])
                writer.writeheader()
                for row in self.algorithm_history:
                    writer.writerow(row)
            self.log(f"Resultados exportados: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar resultados: {e}")
    
    def toggle_log(self):
        """Muestra el panel de Log con la última altura usada o lo oculta completamente."""
        if not hasattr(self, 'log_dock'):
            return
        if self.log_dock.isVisible():
            # Guardar altura actual antes de ocultar
            try:
                self.settings.setValue('log_height', max(60, self.log_dock.height()))
            except Exception:
                pass
            self.log_dock.hide()
        else:
            self.log_dock.show()
            height = int(self.settings.value('log_height', 160))
            try:
                self.resizeDocks([self.log_dock], [max(100, height)], Qt.Vertical)
            except Exception:
                pass

    def changeEvent(self, event):
        """Controla transiciones de estado para evitar saltos raros al minimizar/restaurar."""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            st = self.windowState()
            # Guardar geometría normal antes de minimizar/maximizar
            if not (st & Qt.WindowMinimized) and st == Qt.WindowNoState:
                try:
                    self._normal_geometry = self.geometry()
                except Exception:
                    pass
            # Al restaurar a estado normal, recuperar geometría normal y ajustar a pantalla
            if st == Qt.WindowNoState:
                QTimer.singleShot(0, self.restore_normal_geometry)
        super().changeEvent(event)

    def showEvent(self, event):
        # Evitar reajustes mientras está minimizada
        if not self.isMinimized():
            QTimer.singleShot(0, self.adjust_to_screen)
        super().showEvent(event)

    def closeEvent(self, event):
        # Guardar altura del log al cerrar
        if hasattr(self, 'log_dock') and self.log_dock:
            try:
                self.settings.setValue('log_height', max(60, self.log_dock.height()))
            except Exception:
                pass
        super().closeEvent(event)

    def adjust_to_screen(self):
        """Ajusta tamaño/posición a la geometría disponible de la pantalla actual."""
        if self.isMinimized():
            return
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        g = self.geometry()
        # Clamp size
        new_w = min(g.width(), avail.width())
        new_h = min(g.height(), avail.height())
        new_w = max(800, new_w)
        new_h = max(540, new_h)
        if new_w != g.width() or new_h != g.height():
            self.resize(new_w, new_h)
        # Clamp position (mantener barra de título accesible)
        x = max(avail.x(), min(self.x(), avail.right() - self.width()))
        y = max(avail.y(), min(self.y(), avail.bottom() - self.height()))
        if x != self.x() or y != self.y():
            self.move(x, y)

    def restore_normal_geometry(self):
        """Restaura geometría normal si se guardó y ajusta a pantalla."""
        try:
            if hasattr(self, '_normal_geometry') and self._normal_geometry:
                self.setGeometry(self._normal_geometry)
        except Exception:
            pass
        self.adjust_to_screen()

    def resizeEvent(self, event):
        # Guardar geometría normal durante redimensionamiento en estado normal
        try:
            if self.windowState() == Qt.WindowNoState and not self.isMinimized():
                self._normal_geometry = self.geometry()
        except Exception:
            pass
        super().resizeEvent(event)

    def moveEvent(self, event):
        # Guardar geometría normal durante movimiento en estado normal
        try:
            if self.windowState() == Qt.WindowNoState and not self.isMinimized():
                self._normal_geometry = self.geometry()
        except Exception:
            pass
        super().moveEvent(event)
    
    def search_node(self):
        """Search for node by label or ID"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        for node_id, node in self.canvas.nodes.items():
            if query.lower() in node.label.lower() or query in node_id:
                # Center on node
                pos = self.canvas.world_to_screen(node.pos)
                self.canvas.offset = QPointF(
                    self.canvas.width() / 2 - pos.x(),
                    self.canvas.height() / 2 - pos.y()
                )
                
                # Select node
                self.canvas.selected_nodes.clear()
                self.canvas.selected_nodes.add(node_id)
                
                self.canvas.update()
                self.log(f"Nodo encontrado: {node.label}")
                return
        
        self.log(f"Nodo no encontrado: {query}")
    
    def select_node_from_list(self, item: QListWidgetItem):
        """Select node from the list and center view on it"""
        node_id = item.data(Qt.UserRole)
        if node_id and node_id in self.canvas.nodes:
            node = self.canvas.nodes[node_id]
            # Center on node
            pos = self.canvas.world_to_screen(node.pos)
            self.canvas.offset = QPointF(
                self.canvas.width() / 2 - pos.x(),
                self.canvas.height() / 2 - pos.y()
            )
            # Select node
            self.canvas.selected_nodes.clear()
            self.canvas.selected_nodes.add(node_id)
            self.canvas.update()
            # Load properties panel
            self.load_properties('Nodo', node_id)

    def select_edge_from_list(self, item: QListWidgetItem):
        """Select edge from the list"""
        edge_id = item.data(Qt.UserRole)
        if edge_id and edge_id in self.canvas.edges:
            # Select only this edge
            self.canvas.selected_nodes.clear()
            self.canvas.selected_edges.clear()
            self.canvas.selected_edges.add(edge_id)
            self.canvas.update()
            self.load_properties('Arista', edge_id)
    
    def save_state(self):
        """Save current state to history"""
        state = {
            'nodes': {nid: n.to_dict() for nid, n in self.canvas.nodes.items()},
            'edges': {eid: e.to_dict() for eid, e in self.canvas.edges.items()}
        }
        
        # Remove future history
        self.history = self.history[:self.history_index + 1]
        
        # Add new state
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1
        # Actualizar estado de acciones undo/redo
        if hasattr(self, 'update_undo_redo_actions'):
            self.update_undo_redo_actions()
    
    def undo(self):
        """Undo last action"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index])
            self.log("Deshacer")
        if hasattr(self, 'update_undo_redo_actions'):
            self.update_undo_redo_actions()
    
    def redo(self):
        """Redo last undone action"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index])
            self.log("Rehacer")
        if hasattr(self, 'update_undo_redo_actions'):
            self.update_undo_redo_actions()

    def update_undo_redo_actions(self):
        """Habilita o deshabilita acciones de deshacer/rehacer según el historial."""
        can_undo = self.history_index > 0
        can_redo = self.history_index < len(self.history) - 1
        for act in [getattr(self, 'undo_menu_action', None), getattr(self, 'undo_toolbar_action', None)]:
            if act is not None:
                act.setEnabled(can_undo)
        for act in [getattr(self, 'redo_menu_action', None), getattr(self, 'redo_toolbar_action', None)]:
            if act is not None:
                act.setEnabled(can_redo)
    
    def restore_state(self, state):
        """Restore graph state"""
        self.canvas.nodes = {
            nid: NodeData.from_dict(n) for nid, n in state['nodes'].items()
        }
        self.canvas.edges = {
            eid: EdgeData.from_dict(e) for eid, e in state['edges'].items()
        }
        # Ensure node counter is up-to-date
        if self.canvas.nodes:
            max_node_num = 0
            for node_id, node in self.canvas.nodes.items():
                if node.label.startswith('N') and node.label[1:].isdigit():
                    num = int(node.label[1:])
                    if num > max_node_num:
                        max_node_num = num
            self.canvas.node_counter = max_node_num
        else:
            self.canvas.node_counter = 0
            
        self.canvas.selected_nodes.clear()
        self.canvas.selected_edges.clear()
        self.canvas.highlighted_nodes.clear()
        self.canvas.highlighted_edges.clear()
        self.canvas.update()
    
    # ========================================================================
    # FILE OPERATIONS
    # ========================================================================
    
    def new_graph(self):
        """Create new graph"""
        reply = QMessageBox.question(
            self,
            'Nuevo grafo',
            '¿Está seguro de que desea crear un nuevo grafo? Se perderán los cambios no guardados.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.canvas.clear_graph()
            self.history.clear()
            self.history_index = -1
            self.current_file_path = None
            self.log("Nuevo grafo creado")
            # Guarda estado inicial vacío y actualiza botones
            self.save_state()
    
    def open_graph(self):
        """Importa un grafo desde varios formatos: JSON, GraphML, DOT, CSV (lista o matriz)."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir grafo",
            "",
            "Graph Files (*.json *.graphml *.dot *.csv);;All Files (*)"
        )
        if not filename:
            return
        ext = Path(filename).suffix.lower()
        try:
            self.canvas.clear_graph()
            loaded_labels = []
            if ext == '.json':
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'nodes' not in data or 'edges' not in data:
                    raise ValueError('Formato JSON inválido')
                for nd in data['nodes']:
                    node = NodeData.from_dict(nd)
                    self.canvas.nodes[node.id] = node
                    loaded_labels.append(node.label)
                for ed in data['edges']:
                    edge = EdgeData.from_dict(ed)
                    if edge.source in self.canvas.nodes and edge.target in self.canvas.nodes:
                        self.canvas.edges[edge.id] = edge
            elif ext == '.graphml':
                if not HAS_NETWORKX:
                    raise RuntimeError('NetworkX requerido para GraphML')
                import networkx as nx
                G = nx.read_graphml(filename)
                # Usar label si existe; de lo contrario el id original
                label_map = {}
                for n, attrs in G.nodes(data=True):
                    nid = str(uuid.uuid4())
                    label = attrs.get('label', str(n))
                    node = NodeData(id=nid, label=label, pos=(len(self.canvas.nodes)*50.0, len(self.canvas.nodes)*30.0))
                    self.canvas.nodes[nid] = node
                    label_map[n] = nid
                    loaded_labels.append(label)
                for u, v, d in G.edges(data=True):
                    su = label_map.get(u); tv = label_map.get(v)
                    if su and tv:
                        w = float(d.get('weight', 1.0))
                        self.canvas.add_edge(su, tv, weight=w)
            elif ext == '.dot':
                if not HAS_NETWORKX:
                    raise RuntimeError('NetworkX requerido para DOT')
                try:
                    import networkx as nx
                    from networkx.drawing.nx_pydot import read_dot
                    G = read_dot(filename)
                except Exception as e:
                    raise RuntimeError(f'Error leyendo DOT (pydot requerido): {e}')
                label_map = {}
                for n in G.nodes():
                    nid = str(uuid.uuid4())
                    label = str(n)
                    node = NodeData(id=nid, label=label, pos=(len(self.canvas.nodes)*50.0, len(self.canvas.nodes)*30.0))
                    self.canvas.nodes[nid] = node
                    label_map[n] = nid
                    loaded_labels.append(label)
                for u, v in G.edges():
                    su = label_map.get(u); tv = label_map.get(v)
                    if su and tv:
                        self.canvas.add_edge(su, tv, weight=1.0)
            elif ext == '.csv':
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                if not lines:
                    raise ValueError('CSV vacío')
                header = [h.strip().lower() for h in lines[0].split(',')]
                if {'source','target'} <= set(header):
                    # Lista de aristas
                    def ensure_node(label):
                        for nid, nd in self.canvas.nodes.items():
                            if nd.label == label:
                                return nid
                        nid = str(uuid.uuid4())
                        node = NodeData(id=nid, label=label, pos=(len(self.canvas.nodes)*50.0, len(self.canvas.nodes)*30.0))
                        self.canvas.nodes[nid] = node
                        loaded_labels.append(label)
                        return nid
                    for ln in lines[1:]:
                        parts = [p.strip() for p in ln.split(',')]
                        row = dict(zip(header, parts))
                        su = ensure_node(row['source'])
                        tv = ensure_node(row['target'])
                        w = float(row.get('weight', '1') or 1)
                        self.canvas.add_edge(su, tv, weight=w)
                else:
                    # Matriz de adyacencia
                    matrix = []
                    for ln in lines:
                        parts = [p.strip() for p in ln.split(',')]
                        matrix.append([float(x) for x in parts])
                    n = len(matrix)
                    ids = []
                    for i in range(n):
                        nid = str(uuid.uuid4())
                        label = f'N{i+1}'
                        node = NodeData(id=nid, label=label, pos=(i*65.0, i*35.0))
                        self.canvas.nodes[nid] = node
                        ids.append(nid); loaded_labels.append(label)
                    for i in range(n):
                        for j in range(n):
                            w = matrix[i][j]
                            if w != 0:
                                self.canvas.add_edge(ids[i], ids[j], weight=w)
            else:
                raise ValueError('Formato no soportado')
            # Actualizar contador autolabel
            max_num = 0
            for lb in loaded_labels:
                if lb.startswith('N') and lb[1:].isdigit():
                    max_num = max(max_num, int(lb[1:]))
            self.canvas.node_counter = max_num
            self.canvas.update(); self.save_state()
            self.log(f'Grafo importado: {filename}')
            self.current_file_path = filename
            self.add_recent_file(filename)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'No se pudo importar el grafo:\n{e}')
    
    def save_graph(self):
        """Save graph to JSON file (uses current path if available)"""
        if not self.canvas.nodes:
            QMessageBox.warning(
                self,
                "Grafo vacío",
                "No hay nodos para guardar."
            )
            return
        
        filename = self.current_file_path
        if not filename:
            # Ask for location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar grafo",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            if not filename:
                return
        
        try:
            data = {
                'nodes': [n.to_dict() for n in self.canvas.nodes.values()],
                'edges': [e.to_dict() for e in self.canvas.edges.values()]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Grafo guardado: {filename}")
            self.current_file_path = filename
            self.add_recent_file(filename)
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo guardar el grafo:\n{str(e)}"
            )

    def save_graph_as(self):
        """Save graph to a new file"""
        old_path = self.current_file_path
        self.current_file_path = None
        try:
            self.save_graph()
        finally:
            # keep new path if set; otherwise restore
            if self.current_file_path is None and old_path is not None:
                self.current_file_path = old_path
    
    def export_png(self):
        """Export graph as PNG image"""
        if not self.canvas.nodes:
            QMessageBox.warning(
                self,
                "Grafo vacío",
                "No hay nodos para exportar."
            )
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar PNG",
            "",
            "PNG Files (*.png);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            pixmap = self.canvas.grab()
            pixmap.save(filename, 'PNG')
            self.log(f"Imagen exportada: {filename}")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo exportar la imagen:\n{str(e)}"
            )

    def export_svg(self):
        """Exportar como SVG vectorial (si QtSvg disponible)"""
        if not HAS_QTSVG:
            QMessageBox.warning(self, "SVG no disponible", "QtSvg no está instalado. No se puede exportar SVG.")
            return
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos para exportar.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar SVG", "", "SVG Files (*.svg)")
        if not filename:
            return
        try:
            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(self.canvas.size())
            generator.setViewBox(self.canvas.rect())
            painter = QPainter(generator)
            # Renderiza el canvas completo
            self.canvas.render(painter)
            painter.end()
            self.log(f"SVG exportado: {filename}")
            QMessageBox.information(self, "Éxito", "SVG exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar SVG:\n{str(e)}")
    
    def export_pdf(self):
        """Exporta el canvas a PDF usando QPrinter."""
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos para exportar.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "", "PDF Files (*.pdf)")
        if not filename:
            return
        try:
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filename)
            printer.setFullPage(True)
            painter = QPainter(printer)
            self.canvas.render(painter)
            painter.end()
            self.log(f"PDF exportado: {filename}")
            QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar PDF:\n{e}")
    
    def clear_graph(self):
        """Clear graph"""
        reply = QMessageBox.question(
            self,
            'Limpiar grafo',
            '¿Está seguro de que desea limpiar el grafo?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.canvas.clear_graph()
            self.log("Grafo limpiado")
    
    def toggle_grid(self, checked: bool):
        """Toggle grid visibility"""
        self.canvas.show_grid = checked
        self.canvas.update()
    
    def toggle_snap(self, checked: bool):
        """Toggle snap to grid"""
        self.canvas.snap_to_grid = checked
    
    def show_preferences(self):
        """Show preferences dialog"""
        dialog = PreferencesDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.apply_theme()
            self.canvas.load_preferences()
            self.canvas.update()
            self.log("Preferencias actualizadas")

    def set_theme_checked(self, checked: bool):
        self.settings.setValue('theme', 'Dark' if checked else 'Light')
        self.apply_theme()
        self.theme_label.setText(f"Tema: {'Dark' if checked else 'Light'}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "Acerca de Grafos GUI",
            "<h2> --- Grafos Models Interface --- </h2>"
            "<p>Herramienta completa para visualización y análisis de grafos</p>"
            "<p><b>Características:</b></p>"
            "<ul>"
            "<li>Edición interactiva de grafos</li>"
            "<li>Visualización 2D y 3D</li>"
            "<li>Algoritmos clásicos (BFS, DFS, Dijkstra, Kruskal)</li>"
            "<li>Temas claro/oscuro</li>"
            "<li>Deshacer/Rehacer</li>"
            "<li>Guardar/Cargar JSON</li>"
            "</ul>"
            "<p> Desarrollado por Erodev_08 </p>"
            "<p>Versión 2.0</p>"
        )
    
    # ========================================================================
    # ALGORITMOS
    # ========================================================================
    
    def run_bfs(self):
        """Run BFS algorithm"""
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return

        # Get start node
        node_labels = [n.label for n in self.canvas.nodes.values()]
        start_label, ok = QInputDialog.getItem(
            self,
            "BFS",
            "Seleccione el nodo inicial:",
            node_labels,
            0,
            False
        )

        if not ok:
            return

        # Find node by label
        start_id = next((nid for nid, node in self.canvas.nodes.items() if node.label == start_label), None)
        if start_id is None:
            QMessageBox.warning(self, "Nodo no encontrado", "No se pudo localizar el nodo inicial seleccionado.")
            return

        # Preguntar si se desea buscar un camino objetivo o hacer recorrido completo
        choice = QMessageBox.question(self, "BFS", "¿Desea buscar un camino hasta un nodo objetivo?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if choice == QMessageBox.Yes:
            # Pedir nodo final
            end_label, ok = QInputDialog.getItem(
                self,
                "BFS - Camino",
                "Seleccione el nodo final:",
                node_labels,
                0,
                False
            )
            if not ok:
                return

            end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
            if end_id is None:
                QMessageBox.warning(self, "Nodo no encontrado", "No se pudo localizar el nodo final seleccionado.")
                return

            if end_id == start_id:
                QMessageBox.information(self, "BFS", "Nodo inicial y final son el mismo.")
                self.canvas.highlight_nodes([start_id])
                self.log(f"BFS: inicio y fin iguales ({start_label})")
                self.show_algorithm_summary('BFS', True, "BFS completado", f"Inicio y fin son {start_label}")
                return

            # BFS para encontrar camino más corto (en grafo no ponderado)
            visited = set([start_id])
            parent = {start_id: None}
            parent_edge = {}
            queue = deque([start_id])
            steps = []
            found = False

            # estado inicial
            steps.append({'nodes': [start_id], 'edges': []})

            while queue and not found:
                current = queue.popleft()
                # recorrer aristas para vecinos
                for edge in self.canvas.edges.values():
                    neighbor = None
                    if edge.source == current:
                        neighbor = edge.target
                    elif not edge.directed and edge.target == current:
                        neighbor = edge.source

                    if neighbor is not None and neighbor not in visited:
                        visited.add(neighbor)
                        parent[neighbor] = current
                        parent_edge[neighbor] = edge.id
                        queue.append(neighbor)
                        # agregar paso intermedio
                        steps.append({'nodes': list(visited), 'edges': list(parent_edge.values())})
                        if neighbor == end_id:
                            found = True
                            break

            if not found:
                QMessageBox.warning(self, "Sin camino", f"No existe un camino entre {start_label} y {end_label}.")
                self.show_algorithm_summary('BFS', False, "BFS finalizado", f"No existe camino entre {start_label} y {end_label}.")
                return

            # reconstruir camino
            path = []
            path_edges = []
            cur = end_id
            while cur is not None:
                path.append(cur)
                if cur in parent_edge:
                    path_edges.append(parent_edge[cur])
                cur = parent.get(cur)
            path = list(reversed(path))
            path_edges = list(reversed(path_edges))

            # animar o resaltar camino encontrado
            if getattr(self, 'animate_algorithms', False) and steps:
                # añadir paso final con camino
                steps.append({'nodes': path, 'edges': path_edges})
                self.canvas.animation_controller.set_steps(steps)
                try:
                    speed = int(self.settings.value('anim_speed_ms', 1000))
                    self.canvas.animation_controller.set_speed(speed)
                except Exception:
                    pass
                self.canvas.animation_controller.start()
            else:
                self.canvas.highlight_nodes(path)
                self.canvas.highlight_edges(path_edges)

            path_labels = [self.canvas.nodes[nid].label for nid in path]
            txt = f"BFS camino: {' → '.join(path_labels)}"
            self.log(txt)
            summary = f"BFS completado. Camino de {start_label} a {end_label}"
            details = txt
            self.show_algorithm_summary('BFS', True, summary, details)

        else:
            # Recorrido completo (BFS clásico)
            visited = set()
            queue = deque([start_id])
            visited.add(start_id)
            order = []
            edges_used = []
            steps = []

            while queue:
                current = queue.popleft()
                order.append(self.canvas.nodes[current].label)
                steps.append({'nodes': list(visited), 'edges': list(edges_used)})

                # Find neighbors
                for edge in self.canvas.edges.values():
                    neighbor = None
                    if edge.source == current and edge.target not in visited:
                        neighbor = edge.target
                        edges_used.append(edge.id)
                    elif not edge.directed and edge.target == current and edge.source not in visited:
                        neighbor = edge.source
                        edges_used.append(edge.id)

                    if neighbor:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        steps.append({'nodes': list(visited), 'edges': list(edges_used)})

            # Animar o resaltar final
            if getattr(self, 'animate_algorithms', False) and steps:
                self.canvas.animation_controller.set_steps(steps)
                try:
                    speed = int(self.settings.value('anim_speed_ms', 1000))
                    self.canvas.animation_controller.set_speed(speed)
                except Exception:
                    pass
                self.canvas.animation_controller.start()
            else:
                self.canvas.highlight_nodes(list(visited))
                self.canvas.highlight_edges(edges_used)

            summary = f"BFS completado. Nodos visitados: {len(visited)}"
            details = 'Orden: ' + ' → '.join(order)
            self.log(f"BFS desde {start_label}: {' → '.join(order)}")
            self.show_algorithm_summary('BFS', True, summary, details)
    
    def run_dfs(self):
        """Run DFS algorithm"""
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        # Get start node
        node_labels = [n.label for n in self.canvas.nodes.values()]
        start_label, ok = QInputDialog.getItem(
            self,
            "DFS",
            "Seleccione el nodo inicial:",
            node_labels,
            0,
            False
        )
        
        if not ok:
            return
        
        # Find node by label
        start_id = None
        for nid, node in self.canvas.nodes.items():
            if node.label == start_label:
                start_id = nid
                break
        
        if start_id is None:
            return
        
        # Run DFS
        visited = set()
        order = []
        edges_used = []
        
        def dfs(node_id):
            visited.add(node_id)
            order.append(self.canvas.nodes[node_id].label)
            
            for edge in self.canvas.edges.values():
                neighbor = None
                if edge.source == node_id and edge.target not in visited:
                    neighbor = edge.target
                    edges_used.append(edge.id)
                elif not edge.directed and edge.target == node_id and edge.source not in visited:
                    neighbor = edge.source
                    edges_used.append(edge.id)
                
                if neighbor:
                    dfs(neighbor)
        
        dfs(start_id)
        
        # Highlight results
        self.canvas.highlight_nodes(list(visited))
        self.canvas.highlight_edges(edges_used)
        
        summary = f"DFS completado. Nodos visitados: {len(visited)}"
        details = 'Orden: ' + ' → '.join(order)
        self.log(f"DFS desde {start_label}: {' → '.join(order)}")
        self.show_algorithm_summary('DFS', True, summary, details)
    
    def run_dijkstra(self):
        """Run Dijkstra's algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(
                self,
                "NetworkX no disponible",
                "Se requiere NetworkX para ejecutar Dijkstra."
            )
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        # Get start and end nodes
        node_labels = [n.label for n in self.canvas.nodes.values()]
        
        start_label, ok = QInputDialog.getItem(
            self,
            "Dijkstra",
            "Seleccione el nodo inicial:",
            node_labels,
            0,
            False
        )
        
        if not ok:
            return
        
        end_label, ok = QInputDialog.getItem(
            self,
            "Dijkstra",
            "Seleccione el nodo final:",
            node_labels,
            0,
            False
        )
        
        if not ok:
            return
        
        # Find nodes by label
        start_id = None
        end_id = None
        for nid, node in self.canvas.nodes.items():
            if node.label == start_label:
                start_id = nid
            if node.label == end_label:
                end_id = nid
        
        if start_id is None or end_id is None:
            return
        
        # Build NetworkX graph
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        try:
            # Run Dijkstra con captura de pasos
            # Implementación manual para generar estados si animación activada
            if getattr(self, 'animate_algorithms', False):
                import heapq
                dist = {nid: float('inf') for nid in self.canvas.nodes}
                prev = {}
                dist[start_id] = 0.0
                pq = [(0.0, start_id)]
                settled = set()
                steps = []
                while pq:
                    d, u = heapq.heappop(pq)
                    if u in settled:
                        continue
                    settled.add(u)
                    # Paso: nodo extraído + distancias actuales
                    steps.append({'nodes': list(settled), 'edges': [], 'info': f'Extrae {self.canvas.nodes[u].label} dist={d:.1f}'})
                    if u == end_id:
                        break
                    for edge in self.canvas.edges.values():
                        # Considerar dirección según global
                        if edge.source == u or (not edge.directed and edge.target == u):
                            v = edge.target if edge.source == u else edge.source
                            nd = d + edge.weight
                            if nd < dist[v]:
                                dist[v] = nd
                                prev[v] = (u, edge.id)
                                heapq.heappush(pq, (nd, v))
                                # Paso actualización
                                path_edges_temp = [eid for (_, eid) in prev.values()]
                                steps.append({'nodes': list(settled), 'edges': path_edges_temp, 'info': f'Relaja {self.canvas.nodes[v].label} nueva dist={nd:.1f}'})
                # Reconstruir camino
                path = []
                path_edges = []
                cur = end_id
                while cur in prev or cur == start_id:
                    path.append(cur)
                    if cur == start_id:
                        break
                    pnode, peid = prev[cur]
                    path_edges.append(peid)
                    cur = pnode
                path = list(reversed(path))
                path_edges = list(reversed(path_edges))
                # Añadir último paso camino final
                if path:
                    steps.append({'nodes': path, 'edges': path_edges, 'info': f'Camino final distancia={dist[end_id]:.1f}'})
                self.canvas.animation_controller.set_steps(steps)
                self.canvas.animation_controller.start()
                path_labels = [self.canvas.nodes[nid].label for nid in path]
                logtxt = f"Dijkstra animado: {' → '.join(path_labels)} (distancia: {dist[end_id]:.1f})"
                self.log(logtxt)
                summary = f"Dijkstra completado (animado). Camino de {start_label} a {end_label}"
                details = 'Camino: ' + ' → '.join(path_labels) + f"\nDistancia: {dist[end_id]:.1f}"
                self.show_algorithm_summary('Dijkstra', True, summary, details)
            else:
                path = nx.shortest_path(G, start_id, end_id, weight='weight')
                distance = nx.shortest_path_length(G, start_id, end_id, weight='weight')
                # Find edges in path
                edges_in_path = []
                for i in range(len(path) - 1):
                    for edge_id, edge in self.canvas.edges.items():
                        if (edge.source == path[i] and edge.target == path[i+1]) or \
                           (not edge.directed and edge.target == path[i] and edge.source == path[i+1]):
                            edges_in_path.append(edge_id)
                            break
                self.canvas.highlight_nodes(path)
                self.canvas.highlight_edges(edges_in_path)
                path_labels = [self.canvas.nodes[nid].label for nid in path]
                logtxt = f"Dijkstra: {' → '.join(path_labels)} (distancia: {distance:.1f})"
                self.log(logtxt)
                summary = f"Dijkstra completado. Camino de {start_label} a {end_label}"
                details = 'Camino: ' + ' → '.join(path_labels) + f"\nDistancia: {distance:.1f}"
                self.show_algorithm_summary('Dijkstra', True, summary, details)
        
        except nx.NetworkXNoPath:
            QMessageBox.warning(
                self,
                "Sin camino",
                f"No existe un camino entre {start_label} y {end_label}."
            )
    
    def run_kruskal(self):
        """Run Kruskal's algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(
                self,
                "NetworkX no disponible",
                "Se requiere NetworkX para ejecutar Kruskal."
            )
            return
        
        if not self.canvas.nodes or not self.canvas.edges:
            QMessageBox.warning(
                self,
                "Grafo insuficiente",
                "Se requieren nodos y aristas para ejecutar Kruskal."
            )
            return
        
        # Build NetworkX graph
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        try:
            # Run Kruskal
            mst = nx.minimum_spanning_tree(G, weight='weight')
            
            # Find edges in MST
            mst_edges = []
            total_weight = 0
            for u, v in mst.edges():
                for edge_id, edge in self.canvas.edges.items():
                    if (edge.source == u and edge.target == v) or \
                       (edge.source == v and edge.target == u):
                        mst_edges.append(edge_id)
                        total_weight += edge.weight
                        break
            
            # Highlight results
            self.canvas.highlight_nodes(list(mst.nodes()))
            self.canvas.highlight_edges(mst_edges)
            
            txt = f"Kruskal: MST con {len(mst_edges)} aristas (peso total: {total_weight:.1f})"
            self.log(txt)
            summary = "Kruskal completado. MST calculado"
            details = txt
            self.show_algorithm_summary('Kruskal', True, summary, details)
        
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo calcular el MST:\n{str(e)}"
            )
    
    
    def run_bellman_ford(self):
        """Run Bellman-Ford algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar Bellman-Ford.")
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        node_labels = [n.label for n in self.canvas.nodes.values()]
        start_label, ok = QInputDialog.getItem(self, "Bellman-Ford", 
                                               "Seleccione el nodo inicial:", 
                                               node_labels, 0, False)
        if not ok:
            return
        
        end_label, ok = QInputDialog.getItem(self, "Bellman-Ford", 
                                             "Seleccione el nodo final:", 
                                             node_labels, 0, False)
        if not ok:
            return
        
        start_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == start_label), None)
        end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
        
        if start_id is None or end_id is None:
            return
        
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        try:
            path = nx.bellman_ford_path(G, start_id, end_id, weight='weight')
            distance = nx.bellman_ford_path_length(G, start_id, end_id, weight='weight')
            
            edges_in_path = []
            for i in range(len(path) - 1):
                for edge_id, edge in self.canvas.edges.items():
                    if (edge.source == path[i] and edge.target == path[i+1]) or \
                       (not edge.directed and edge.target == path[i] and edge.source == path[i+1]):
                        edges_in_path.append(edge_id)
                        break
            
            self.canvas.highlight_nodes(path)
            self.canvas.highlight_edges(edges_in_path)
            
            path_labels = [self.canvas.nodes[nid].label for nid in path]
            txt = f"Bellman-Ford: {' → '.join(path_labels)} (distancia: {distance:.1f})"
            self.log(txt)
            summary = f"Bellman-Ford completado. Camino de {start_label} a {end_label}"
            details = txt
            self.show_algorithm_summary('Bellman-Ford', True, summary, details)
        
        except nx.NetworkXNoPath:
            QMessageBox.warning(self, "Sin camino", f"No existe un camino entre {start_label} y {end_label}.")
        except nx.NetworkXUnbounded:
            QMessageBox.critical(self, "Ciclo negativo", "Se detectó un ciclo de peso negativo que hace ilimitadas las distancias.")
            self.log("Bellman-Ford: ciclo negativo detectado")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Falló Bellman-Ford: {e}")
    
    def run_floyd_warshall(self):
        """Run Floyd-Warshall algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar Floyd-Warshall.")
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        distances = dict(nx.floyd_warshall(G, weight='weight'))
        # Detección de ciclos negativos: distancia(v,v) < 0
        negatives = [nid for nid in G.nodes() if distances[nid][nid] < 0]
        if negatives:
            labels = [self.canvas.nodes[n].label for n in negatives]
            QMessageBox.critical(self, "Ciclos negativos", f"Se detectaron ciclos negativos en nodos: {', '.join(labels)}")
            self.log("Floyd-Warshall: ciclos negativos detectados")
        
        # Show results in a dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Floyd-Warshall - Distancias entre todos los pares")
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        node_list = list(self.canvas.nodes.keys())
        table.setRowCount(len(node_list))
        table.setColumnCount(len(node_list))
        
        labels = [self.canvas.nodes[nid].label for nid in node_list]
        table.setHorizontalHeaderLabels(labels)
        table.setVerticalHeaderLabels(labels)
        
        for i, src in enumerate(node_list):
            for j, tgt in enumerate(node_list):
                dist = distances[src][tgt]
                item = QTableWidgetItem(f"{dist:.1f}" if dist != float('inf') else "∞")
                table.setItem(i, j, item)
        
        table.resizeColumnsToContents()
        layout.addWidget(table)
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
        txt = "Floyd-Warshall: Calculadas distancias entre todos los pares"
        self.log(txt)
        summary = "Floyd-Warshall completado"
        details = txt
        self.show_algorithm_summary('Floyd-Warshall', True, summary, details)
        
    def run_astar(self):
        """Run A* algorithm with Euclidean heuristic"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar A*.")
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        node_labels = [n.label for n in self.canvas.nodes.values()]
        start_label, ok = QInputDialog.getItem(self, "A*", 
                                               "Seleccione el nodo inicial:", 
                                               node_labels, 0, False)
        if not ok:
            return
        
        end_label, ok = QInputDialog.getItem(self, "A*", 
                                             "Seleccione el nodo final:", 
                                             node_labels, 0, False)
        if not ok:
            return
        
        start_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == start_label), None)
        end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
        
        if start_id is None or end_id is None:
            return
        
        # Euclidean heuristic
        def heuristic(u, v):
            pos_u = self.canvas.nodes[u].pos
            pos_v = self.canvas.nodes[v].pos
            return math.sqrt((pos_u[0] - pos_v[0])**2 + (pos_u[1] - pos_v[1])**2)
        
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        try:
            path = nx.astar_path(G, start_id, end_id, heuristic=heuristic, weight='weight')
            distance = nx.astar_path_length(G, start_id, end_id, heuristic=heuristic, weight='weight')
            
            edges_in_path = []
            for i in range(len(path) - 1):
                for edge_id, edge in self.canvas.edges.items():
                    if (edge.source == path[i] and edge.target == path[i+1]) or \
                       (not edge.directed and edge.target == path[i] and edge.source == path[i+1]):
                        edges_in_path.append(edge_id)
                        break
            
            self.canvas.highlight_nodes(path)
            self.canvas.highlight_edges(edges_in_path)
            
            path_labels = [self.canvas.nodes[nid].label for nid in path]
            txt = f"A*: {' → '.join(path_labels)} (distancia: {distance:.1f})"
            self.log(txt)
            summary = f"A* completado. Camino de {start_label} a {end_label}"
            details = txt
            self.show_algorithm_summary('A*', True, summary, details)
        
        except nx.NetworkXNoPath:
            QMessageBox.warning(self, "Sin camino", 
                              f"No existe un camino entre {start_label} y {end_label}.")
    
    def run_prim(self):
        """Run Prim's algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar Prim.")
            return
        
        if not self.canvas.nodes or not self.canvas.edges:
            QMessageBox.warning(self, "Grafo insuficiente", 
                              "Se requieren nodos y aristas para ejecutar Prim.")
            return
        
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        try:
            mst = nx.minimum_spanning_tree(G, algorithm='prim', weight='weight')
            
            mst_edges = []
            total_weight = 0
            for u, v in mst.edges():
                for edge_id, edge in self.canvas.edges.items():
                    if (edge.source == u and edge.target == v) or \
                       (edge.source == v and edge.target == u):
                        mst_edges.append(edge_id)
                        total_weight += edge.weight
                        break
            
            self.canvas.highlight_nodes(list(mst.nodes()))
            self.canvas.highlight_edges(mst_edges)
            
            txt = f"Prim: MST con {len(mst_edges)} aristas (peso total: {total_weight:.1f})"
            self.log(txt)
            summary = "Prim completado. MST calculado"
            details = txt
            self.show_algorithm_summary('Prim', True, summary, details)
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo calcular el MST:\n{str(e)}")
    
    def run_topological_sort(self):
        """Run topological sort"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar ordenamiento topológico.")
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        # Check if graph is directed
        has_directed = any(edge.directed for edge in self.canvas.edges.values())
        if not has_directed:
            QMessageBox.warning(self, "Grafo no dirigido", 
                              "El ordenamiento topológico requiere un grafo dirigido.")
            return
        
        G = nx.DiGraph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            if edge.directed:
                G.add_edge(edge.source, edge.target)
        
        try:
            topo_order = list(nx.topological_sort(G))
            labels = [self.canvas.nodes[nid].label for nid in topo_order]
            
            self.canvas.highlight_nodes(topo_order)
            txt = f"Ordenamiento Topológico: {' → '.join(labels)}"
            self.log(txt)
            summary = "Ordenamiento topológico completado"
            details = txt
            self.show_algorithm_summary('Topológico', True, summary, details)
        
        except nx.NetworkXError:
            QMessageBox.warning(self, "Ciclo detectado", 
                              "El grafo contiene ciclos. No se puede realizar ordenamiento topológico.")
    
    def run_tarjan_scc(self):
        """Run Tarjan's strongly connected components algorithm"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para ejecutar Tarjan.")
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(self, "Grafo vacío", "No hay nodos en el grafo.")
            return
        
        G = nx.DiGraph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            if edge.directed:
                G.add_edge(edge.source, edge.target)
        
        sccs = list(nx.strongly_connected_components(G))
        
        result = f"Componentes Fuertemente Conexas: {len(sccs)}\n\n"
        for i, scc in enumerate(sccs, 1):
            labels = [self.canvas.nodes[nid].label for nid in scc]
            result += f"Componente {i}: {', '.join(labels)}\n"
        
        QMessageBox.information(self, "Tarjan SCC", result)
        txt = f"Tarjan: {len(sccs)} componentes fuertemente conexas"
        self.log(txt)
        summary = "Tarjan completado"
        details = txt
        self.show_algorithm_summary('Tarjan SCC', True, summary, details)

    def run_max_flow(self):
        """Máximo flujo (Edmonds-Karp) y corte mínimo"""
        if not self.canvas.nodes or not self.canvas.edges:
            QMessageBox.warning(self, "Grafo vacío", "Se requieren nodos y aristas con capacidades (peso).")
            return
        node_labels = [n.label for n in self.canvas.nodes.values()]
        s_label, ok = QInputDialog.getItem(self, "Máximo flujo", "Fuente:", node_labels, 0, False)
        if not ok:
            return
        t_label, ok = QInputDialog.getItem(self, "Máximo flujo", "Sumidero:", node_labels, 0, False)
        if not ok:
            return
        if s_label == t_label:
            QMessageBox.warning(self, "Par inválido", "Fuente y sumidero deben ser diferentes.")
            return
        # Map labels to ids
        def id_by_label(lbl):
            for nid, nd in self.canvas.nodes.items():
                if nd.label == lbl:
                    return nid
            return None
        s = id_by_label(s_label); t = id_by_label(t_label)
        if not s or not t:
            return
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para ejecutar Edmonds-Karp.")
            return
        # Build directed graph with capacities
        G = nx.DiGraph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            if e.directed:
                G.add_edge(e.source, e.target, capacity=e.weight)
            else:
                G.add_edge(e.source, e.target, capacity=e.weight)
                G.add_edge(e.target, e.source, capacity=e.weight)
        try:
            flow_value, flow_dict = nx.maximum_flow(G, s, t, capacity='capacity', flow_func=nx.algorithms.flow.edmonds_karp)
            cut_value, (S, T) = nx.minimum_cut(G, s, t, capacity='capacity')
            # Edges with positive flow
            edges_flow = []
            for u, dests in flow_dict.items():
                for v, f in dests.items():
                    if f > 0:
                        for eid, ed in self.canvas.edges.items():
                            if ed.source == u and ed.target == v:
                                edges_flow.append(eid); break
            # Min-cut edges S->T
            edges_cut = []
            for eid, ed in self.canvas.edges.items():
                if ed.source in S and ed.target in T:
                    edges_cut.append(eid)
            self.canvas.highlight_edges(list(set(edges_flow + edges_cut)))
            self.canvas.highlight_nodes(list(S | T))
            txt = f"Máximo flujo de {s_label} a {t_label}: {flow_value:.1f} | Corte mínimo: {cut_value:.1f}"
            self.log(txt)
            summary = "Máximo flujo completado"
            details = txt
            self.show_algorithm_summary('Max Flow', True, summary, details)
        except Exception as e:
            QMessageBox.warning(self, "Error en flujo", str(e))

    def run_cycle_detection(self):
        """Detectar ciclos: dirigidos (Johnson) y no dirigidos (basis)"""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para detectar ciclos.")
            return
        Gd = nx.DiGraph(); Gu = nx.Graph()
        for nid in self.canvas.nodes:
            Gd.add_node(nid); Gu.add_node(nid)
        for e in self.canvas.edges.values():
            if e.directed:
                Gd.add_edge(e.source, e.target)
                Gu.add_edge(e.source, e.target)
            else:
                Gu.add_edge(e.source, e.target)
        cycles_dir = list(nx.simple_cycles(Gd))
        cycles_und = nx.cycle_basis(Gu)
        total = len(cycles_dir) + len(cycles_und)
        if total == 0:
            self.log("No se encontraron ciclos.")
            self.canvas.clear_highlights();
            return
        cycle_nodes = cycles_dir[0] if cycles_dir else cycles_und[0]
        cycle_edges = []
        for i in range(len(cycle_nodes)):
            u = cycle_nodes[i]
            v = cycle_nodes[(i+1) % len(cycle_nodes)]
            for eid, ed in self.canvas.edges.items():
                if (ed.source == u and ed.target == v) or (not ed.directed and ed.source == v and ed.target == u):
                    cycle_edges.append(eid); break
        self.canvas.highlight_nodes(cycle_nodes)
        self.canvas.highlight_edges(cycle_edges)
        self.log(f"Ciclos detectados: {total} (Dirigidos={len(cycles_dir)}, No dirigidos={len(cycles_und)})")

    def run_graph_coloring(self):
        """Coloreo por Welsh-Powell (greedy por grado)"""
        if not self.canvas.nodes:
            return
        def degree(nid):
            deg = 0
            for e in self.canvas.edges.values():
                if e.source == nid or e.target == nid:
                    deg += 1 if not e.directed else (1 if e.source == nid else 0)
            return deg
        order = sorted(self.canvas.nodes.keys(), key=degree, reverse=True)
        color_of = {}
        for nid in order:
            used = set()
            neighbors = set()
            for e in self.canvas.edges.values():
                if e.source == nid:
                    neighbors.add(e.target)
                if not e.directed and e.target == nid:
                    neighbors.add(e.source)
            for nb in neighbors:
                if nb in color_of:
                    used.add(color_of[nb])
            c = 0
            while c in used:
                c += 1
            color_of[nid] = c
        chromatic = max(color_of.values()) + 1 if color_of else 0
        palette = [QColor(231,76,60), QColor(46,204,113), QColor(52,152,219), QColor(155,89,182), QColor(241,196,15), QColor(26,188,156)]
        for nid, c in color_of.items():
            col = palette[c % len(palette)]
            self.canvas.nodes[nid].color = col.getRgb()[:3]
        self.canvas.update(); self.save_state()
        classes = {}
        for nid, c in color_of.items():
            classes.setdefault(c, []).append(self.canvas.nodes[nid].label)
        class_txt = "; ".join([f"C{ci}: {', '.join(lbls)}" for ci, lbls in classes.items()])
        self.log(f"Coloreo Welsh-Powell: {chromatic} colores | {class_txt}")

    def run_communities(self):
        """Comunidades por Girvan-Newman (primer nivel)"""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para comunidades.")
            return
        G = nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target, weight=e.weight)
        try:
            from networkx.algorithms.community import girvan_newman, modularity
            comp = next(girvan_newman(G))
            communities = [list(c) for c in comp]
            try:
                mod = modularity(G, communities)
            except Exception:
                mod = None
            palette = [QColor(231,76,60), QColor(46,204,113), QColor(52,152,219), QColor(155,89,182), QColor(241,196,15), QColor(26,188,156)]
            for i, comm in enumerate(communities):
                col = palette[i % len(palette)].getRgb()[:3]
                for nid in comm:
                    if nid in self.canvas.nodes:
                        self.canvas.nodes[nid].color = col
            self.canvas.update(); self.save_state()
            sizes = [len(c) for c in communities]
            self.log(f"Comunidades (Girvan-Newman): {len(communities)} grupos, tamaños {sizes}" + (f", modularidad {mod:.3f}" if mod is not None else ""))
        except Exception as e:
            QMessageBox.warning(self, "Error comunidades", str(e))

    def run_bipartite_check(self):
        """Verificar si el grafo es bipartito y resaltar particiones"""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para bipartito.")
            return
        G = nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target)
        import networkx.algorithms.bipartite as bip
        if not bip.is_bipartite(G):
            self.log("El grafo NO es bipartito.")
            return
        left, right = bip.sets(G)
        self.canvas.highlight_nodes(list(left | right))
        for nid in left:
            if nid in self.canvas.nodes:
                self.canvas.nodes[nid].color = QColor(52,152,219).getRgb()[:3]
        for nid in right:
            if nid in self.canvas.nodes:
                self.canvas.nodes[nid].color = QColor(231,76,60).getRgb()[:3]
        self.canvas.update(); self.save_state()
        self.log(f"Grafo bipartito. Particiones: L={len(left)}, R={len(right)}")

    def run_maximum_matching(self):
        """Matching máximo en grafo bipartito"""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para matching.")
            return
        G = nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target)
        import networkx.algorithms.bipartite as bip
        if not bip.is_bipartite(G):
            QMessageBox.information(self, "No bipartito", "El grafo no es bipartito; matching general no implementado aún.")
            return
        matching = bip.maximum_matching(G)
        matched_edges = set()
        for u, v in matching.items():
            if (v, u) not in matched_edges:
                matched_edges.add((u, v))
        edge_ids = []
        for u, v in matched_edges:
            for eid, ed in self.canvas.edges.items():
                if {ed.source, ed.target} == {u, v}:
                    edge_ids.append(eid); break
        self.canvas.highlight_edges(edge_ids)
        self.log(f"Matching máximo (bipartito): {len(edge_ids)} aristas")

    def run_eulerian(self):
        """Detecta circuito o camino euleriano (Hierholzer vía NetworkX)."""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para cálculo euleriano.")
            return
        directed = any(e.directed for e in self.canvas.edges.values())
        G = nx.DiGraph() if directed else nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target)
        try:
            if directed:
                if nx.is_eulerian(G):
                    seq = list(nx.eulerian_circuit(G))
                elif nx.is_semieulerian(G):
                    seq = list(nx.eulerian_path(G))
                else:
                    QMessageBox.information(self, "No Euleriano", "El grafo dirigido no es (semi)euleriano.")
                    return
                ids = []
                for u, v in seq:
                    for eid, ed in self.canvas.edges.items():
                        if ed.source == u and ed.target == v:
                            ids.append(eid); break
                self.canvas.highlight_edges(ids)
                self.log(f"Euleriano (dirigido): {len(ids)} aristas")
            else:
                if nx.is_eulerian(G):
                    seq = list(nx.eulerian_circuit(G))
                elif nx.is_semieulerian(G):
                    seq = list(nx.eulerian_path(G))
                else:
                    QMessageBox.information(self, "No Euleriano", "El grafo no es (semi)euleriano.")
                    return
                ids = []
                for u, v in seq:
                    for eid, ed in self.canvas.edges.items():
                        if {ed.source, ed.target} == {u, v}:
                            ids.append(eid); break
                self.canvas.highlight_edges(ids)
                self.log(f"Euleriano: {len(ids)} aristas")
        except Exception as e:
            QMessageBox.warning(self, "Error Euleriano", str(e))

    def check_planarity(self):
        """Verifica si el grafo es planar (usa networkx.check_planarity)."""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para verificar planaridad.")
            return
        G = nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target)
        try:
            planar, _ = nx.check_planarity(G)
            if planar:
                QMessageBox.information(self, "Planaridad", "El grafo es planar.")
                self.log("Planaridad: Sí")
            else:
                QMessageBox.information(self, "Planaridad", "El grafo NO es planar.")
                self.log("Planaridad: No")
        except Exception as e:
            QMessageBox.warning(self, "Error Planaridad", str(e))

    def check_tree(self):
        """Valida si el grafo actual (ignora dirección) es un árbol."""
        if not HAS_NETWORKX:
            QMessageBox.information(self, "NetworkX requerido", "Instale NetworkX para validar árbol.")
            return
        if not self.canvas.nodes:
            QMessageBox.information(self, "Árbol", "Grafo vacío.")
            return
        G = nx.Graph()
        for nid in self.canvas.nodes:
            G.add_node(nid)
        for e in self.canvas.edges.values():
            G.add_edge(e.source, e.target)
        try:
            ok = nx.is_tree(G)
            if ok:
                QMessageBox.information(self, "Árbol", "El grafo es un árbol.")
                self.log("Árbol: Sí")
            else:
                QMessageBox.information(self, "Árbol", "El grafo NO es un árbol.")
                self.log("Árbol: No")
        except Exception as e:
            QMessageBox.warning(self, "Error Árbol", str(e))

    def run_paths_dialog(self):
        """Diálogo para calcular caminos: más corto (Dijkstra) o más largo (DAG)."""
        if not self.canvas.nodes:
            QMessageBox.information(self, "Caminos", "No hay nodos en el grafo.")
            return
        labels = [n.label for n in self.canvas.nodes.values()]
        labels.sort()
        # Selección de tipo
        tipo, ok = QInputDialog.getItem(
            self, "Caminos", "Tipo:", ["Más corto (Dijkstra)", "Más largo (DAG)"], 0, False
        )
        if not ok:
            return
        # Selección de nodos
        start_label, ok = QInputDialog.getItem(self, "Origen", "Nodo origen:", labels, 0, False)
        if not ok:
            return
        end_label, ok = QInputDialog.getItem(self, "Destino", "Nodo destino:", labels, 0, False)
        if not ok:
            return
        start_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == start_label), None)
        end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
        if start_id is None or end_id is None:
            QMessageBox.warning(self, "Caminos", "No se pudieron resolver los nodos seleccionados.")
            return
        if start_id == end_id:
            QMessageBox.information(self, "Caminos", "Origen y destino son el mismo nodo.")
            return
        if "largo" in tipo:
            self.run_longest_path(start_id, end_id)
        else:
            self.run_shortest_path(start_id, end_id)

    def run_shortest_path(self, start_id=None, end_id=None):
        """Calcula camino más corto entre dos nodos con Dijkstra (pesos >= 0)."""
        if not self.canvas.nodes:
            QMessageBox.information(self, "Dijkstra", "No hay nodos en el grafo.")
            return
        # Si no se pasan IDs, pedirlos
        if start_id is None or end_id is None:
            labels = [n.label for n in self.canvas.nodes.values()]
            labels.sort()
            start_label, ok = QInputDialog.getItem(self, "Dijkstra", "Origen:", labels, 0, False)
            if not ok:
                return
            end_label, ok = QInputDialog.getItem(self, "Dijkstra", "Destino:", labels, 0, False)
            if not ok:
                return
            start_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == start_label), None)
            end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
        if start_id is None or end_id is None or start_id == end_id:
            QMessageBox.information(self, "Dijkstra", "Seleccione nodos válidos y distintos.")
            return
        # Validación de pesos (no negativos para Dijkstra)
        try:
            has_negative = any(float(e.weight) < 0 for e in self.canvas.edges.values())
        except Exception:
            has_negative = False
        if has_negative:
            QMessageBox.warning(self, "Dijkstra", "Hay pesos negativos. Use Bellman-Ford o Floyd-Warshall.")
            return
        # Construir grafo de adyacencia
        adj = {nid: [] for nid in self.canvas.nodes.keys()}
        for e in self.canvas.edges.values():
            w = float(e.weight)
            adj[e.source].append((e.target, e.id, w))
            if not e.directed:
                adj[e.target].append((e.source, e.id, w))
        # Dijkstra
        import heapq
        dist = {nid: float('inf') for nid in adj}
        prev = {nid: None for nid in adj}
        prev_edge = {nid: None for nid in adj}
        dist[start_id] = 0.0
        pq = [(0.0, start_id)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == end_id:
                break
            for v, eid, w in adj[u]:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    prev_edge[v] = eid
                    heapq.heappush(pq, (nd, v))
        if dist[end_id] == float('inf'):
            QMessageBox.information(self, "Dijkstra", "No hay camino entre los nodos seleccionados.")
            return
        # Reconstruir camino
        path_nodes = []
        path_edges = []
        cur = end_id
        while cur is not None:
            path_nodes.append(cur)
            if prev_edge[cur] is not None:
                path_edges.append(prev_edge[cur])
            cur = prev[cur]
        path_nodes.reverse(); path_edges.reverse()
        self.canvas.clear_highlights()
        self.canvas.highlight_nodes(path_nodes)
        self.canvas.highlight_edges(path_edges)
        labels = [self.canvas.nodes[nid].label for nid in path_nodes]
        self.log(f"Camino más corto (Dijkstra): {' → '.join(labels)} (distancia: {dist[end_id]:.2f})")

    def run_longest_path(self, start_id=None, end_id=None):
        """Calcula camino más largo en un DAG (usa solo aristas dirigidas)."""
        if not self.canvas.nodes:
            QMessageBox.information(self, "Camino más largo (DAG)", "No hay nodos en el grafo.")
            return
        # Si no se pasan IDs, pedirlos
        if start_id is None or end_id is None:
            labels = [n.label for n in self.canvas.nodes.values()]
            labels.sort()
            start_label, ok = QInputDialog.getItem(self, "Camino más largo (DAG)", "Origen:", labels, 0, False)
            if not ok:
                return
            end_label, ok = QInputDialog.getItem(self, "Camino más largo (DAG)", "Destino:", labels, 0, False)
            if not ok:
                return
            start_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == start_label), None)
            end_id = next((nid for nid, n in self.canvas.nodes.items() if n.label == end_label), None)
        if start_id is None or end_id is None or start_id == end_id:
            QMessageBox.information(self, "Camino más largo (DAG)", "Seleccione nodos válidos y distintos.")
            return
        # Construir grafo dirigido solo con aristas dirigidas
        nodes = list(self.canvas.nodes.keys())
        adj = {nid: [] for nid in nodes}
        indeg = {nid: 0 for nid in nodes}
        has_directed = False
        for e in self.canvas.edges.values():
            if getattr(e, 'directed', False):
                has_directed = True
                w = float(e.weight)
                adj[e.source].append((e.target, e.id, w))
                indeg[e.target] += 1
        if not has_directed:
            QMessageBox.warning(
                self,
                "Camino más largo (DAG)",
                "No hay aristas dirigidas. El camino más largo general es NP-difícil. Use un DAG."
            )
            return
        # Kahn topo
        from collections import deque
        q = deque([u for u in nodes if indeg[u] == 0])
        topo = []
        indeg2 = indeg.copy()
        while q:
            u = q.popleft(); topo.append(u)
            for v, _, _ in adj[u]:
                indeg2[v] -= 1
                if indeg2[v] == 0:
                    q.append(v)
        if len(topo) != len(nodes):
            QMessageBox.warning(self, "Camino más largo (DAG)", "El grafo dirigido tiene ciclos. No se puede calcular el camino más largo.")
            return
        # DP sobre orden topológico
        NEG_INF = float('-inf')
        dist = {nid: NEG_INF for nid in nodes}
        prev = {nid: None for nid in nodes}
        prev_edge = {nid: None for nid in nodes}
        dist[start_id] = 0.0
        for u in topo:
            if dist[u] == NEG_INF:
                continue
            for v, eid, w in adj[u]:
                cand = dist[u] + w
                if cand > dist[v]:
                    dist[v] = cand
                    prev[v] = u
                    prev_edge[v] = eid
        if dist[end_id] == NEG_INF:
            QMessageBox.information(self, "Camino más largo (DAG)", "No hay camino dirigido entre los nodos seleccionados.")
            return
        # Reconstrucción
        path_nodes = []
        path_edges = []
        cur = end_id
        while cur is not None:
            path_nodes.append(cur)
            if prev_edge[cur] is not None:
                path_edges.append(prev_edge[cur])
            cur = prev[cur]
        path_nodes.reverse(); path_edges.reverse()
        self.canvas.clear_highlights()
        self.canvas.highlight_nodes(path_nodes)
        self.canvas.highlight_edges(path_edges)
        labels = [self.canvas.nodes[nid].label for nid in path_nodes]
        self.log(f"Camino más largo (DAG): {' → '.join(labels)} (peso total: {dist[end_id]:.2f})")

    def export_graphml(self):
        """Export graph to GraphML"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para exportar a GraphML.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar GraphML", "", "GraphML Files (*.graphml)"
        )
        if filename:
            if self.canvas.export_graphml(filename):
                self.log(f"Grafo exportado a GraphML: {filename}")
                QMessageBox.information(self, "Éxito", "Grafo exportado correctamente.")
    
    def export_dot(self):
        """Export graph to DOT"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar DOT", "", "DOT Files (*.dot)"
        )
        if filename:
            if self.canvas.export_dot(filename):
                self.log(f"Grafo exportado a DOT: {filename}")
                QMessageBox.information(self, "Éxito", "Grafo exportado correctamente.")
    
    def export_adjacency_matrix(self):
        """Export adjacency matrix"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar Matriz de Adyacencia", "", "CSV Files (*.csv)"
        )
        if filename:
            if self.canvas.export_adjacency_matrix(filename):
                self.log(f"Matriz de adyacencia exportada: {filename}")
                QMessageBox.information(self, "Éxito", "Matriz exportada correctamente.")
    
    def export_edge_list(self):
        """Export edge list"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar Lista de Aristas", "", "CSV Files (*.csv)"
        )
        if filename:
            if self.canvas.export_edge_list(filename):
                self.log(f"Lista de aristas exportada: {filename}")
                QMessageBox.information(self, "Éxito", "Lista exportada correctamente.")
    
    
    def show_graph_generator(self):
        """Show graph generator dialog"""
        dialog = GraphGeneratorDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.result:
            # Clear current graph
            self.canvas.clear_graph()
            
            # Add generated nodes
            node_ids = {}
            for i, label in enumerate(dialog.result['nodes']):
                # Position nodes in a circle
                angle = 2 * math.pi * i / len(dialog.result['nodes'])
                x = 400 + 200 * math.cos(angle)
                y = 300 + 200 * math.sin(angle)
                node_id = self.canvas.add_node((x, y), label)
                node_ids[label] = node_id
            
            # Add generated edges
            for src, tgt, weight in dialog.result['edges']:
                if src in node_ids and tgt in node_ids:
                    self.canvas.add_edge(node_ids[src], node_ids[tgt], weight)
            
            # Auto layout
            self.canvas.auto_layout()
            self.log(f"Grafo generado: {len(dialog.result['nodes'])} nodos, {len(dialog.result['edges'])} aristas")
    
    def show_graph_analysis(self):
        """Show graph analysis dialog"""
        dialog = GraphAnalysisDialog(self.canvas, self)
        dialog.exec_()
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        dialog = ShortcutsDialog(self)
        dialog.exec_()
    
    def color_by_degree(self):
        """Color nodes by degree"""
        if not self.canvas.nodes:
            return
        
        # Calculate degrees
        degrees = {node_id: 0 for node_id in self.canvas.nodes}
        for edge in self.canvas.edges.values():
            degrees[edge.source] += 1
            degrees[edge.target] += 1
        
        max_degree = max(degrees.values()) if degrees else 1
        
        # Color nodes
        for node_id, degree in degrees.items():
            # Color from blue (low degree) to red (high degree)
            ratio = degree / max_degree
            r = int(255 * ratio)
            g = int(100 * (1 - ratio))
            b = int(255 * (1 - ratio))
            self.canvas.nodes[node_id].color = (r, g, b)
        
        self.canvas.update()
        self.log("Nodos coloreados por grado")
    
    def color_by_centrality(self):
        """Color nodes by betweenness centrality"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", 
                              "Se requiere NetworkX para calcular centralidad.")
            return
        
        if not self.canvas.nodes:
            return
        
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        
        centrality = nx.betweenness_centrality(G)
        max_cent = max(centrality.values()) if centrality else 1
        
        # Color nodes
        for node_id, cent in centrality.items():
            ratio = cent / max_cent if max_cent > 0 else 0
            r = int(255 * ratio)
            g = int(100 * (1 - ratio))
            b = int(255 * (1 - ratio))
            self.canvas.nodes[node_id].color = (r, g, b)
        
        self.canvas.update()
        self.log("Nodos coloreados por centralidad de intermediación")

    def highlight_connected_components(self):
        """Resalta componentes conexas; colorea cada componente y resalta la mayor"""
        if not HAS_NETWORKX:
            QMessageBox.warning(self, "NetworkX no disponible", "Instale NetworkX para esta función.")
            return
        if not self.canvas.nodes:
            QMessageBox.information(self, "Componentes", "Grafo vacío.")
            return
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target)
        comps = list(nx.connected_components(G))
        if not comps:
            QMessageBox.information(self, "Componentes", "No se encontraron componentes.")
            return
        palette = [
            (255,100,100),(100,255,100),(100,100,255),(255,200,100),(180,100,255),
            (100,255,200),(255,150,200),(200,255,150)
        ]
        for i, comp in enumerate(comps):
            color = palette[i % len(palette)]
            for nid in comp:
                self.canvas.nodes[nid].color = color
        largest = max(comps, key=len)
        self.canvas.highlight_nodes(list(largest))
        edges_inside = [eid for eid,e in self.canvas.edges.items() if e.source in largest and e.target in largest]
        self.canvas.highlight_edges(edges_inside)
        self.canvas.update()
        self.log(f"{len(comps)} componentes; mayor con {len(largest)} nodos resaltada")
    
    # ========================================================================
    # VISTA 3D
    # ========================================================================
    
    def show_3d_view(self):
        """Show 3D visualization"""
        if not HAS_URSINA:
            QMessageBox.warning(
                self,
                "Ursina no disponible",
                "Se requiere Ursina para la visualización 3D.\n"
                "Instale con: pip install ursina"
            )
            return
        
        if not self.canvas.nodes:
            QMessageBox.warning(
                self,
                "Grafo vacío",
                "No hay nodos para visualizar."
            )
            return
        
        self.log("Abriendo vista 3D...")
        
        # Launch 3D view in separate process
        import multiprocessing
        process = multiprocessing.Process(
            target=launch_3d_view,
            args=(
                {nid: n.to_dict() for nid, n in self.canvas.nodes.items()},
                {eid: e.to_dict() for eid, e in self.canvas.edges.items()},
                self.settings.value('lighting', True, type=bool),
                self.settings.value('shadows', True, type=bool),
                self.settings.value('sky', True, type=bool)
            )
        )
        process.start()


# ============================================================================
# DIALOGO DE GENERADOR DE GRAFO
# ============================================================================

class GraphGeneratorDialog(QDialog):
    """Dialog for generating various types of graphs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generador de Grafos")
        self.setMinimumWidth(400)
        self.result = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Graph type selection
        type_group = QGroupBox("Tipo de Grafo")
        type_layout = QVBoxLayout()
        
        self.graph_types = QComboBox()
        self.graph_types.addItems([
            "Grafo Aleatorio (Erdős-Rényi)",
            "Grafo Completo",
            "Grafo Bipartito Completo",
            "Árbol Aleatorio",
            "Ciclo",
            "Camino",
            "Rueda",
            "Estrella",
            "Rejilla 2D",
            "Grafo Regular",
            "Grafo de Barabási-Albert (Scale-Free)",
            "Grafo de Watts-Strogatz (Small-World)"
        ])
        self.graph_types.currentIndexChanged.connect(self.update_parameters)
        type_layout.addWidget(self.graph_types)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Parameters
        param_group = QGroupBox("Parámetros")
        self.param_layout = QFormLayout()
        param_group.setLayout(self.param_layout)
        layout.addWidget(param_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(self.generate)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.update_parameters()
    
    def update_parameters(self):
        # Clear existing parameters
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        graph_type = self.graph_types.currentIndex()
        
        if graph_type == 0:  # Random
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 1000)
            self.n_spin.setValue(10)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
            self.p_spin = QDoubleSpinBox()
            self.p_spin.setRange(0.0, 1.0)
            self.p_spin.setSingleStep(0.1)
            self.p_spin.setValue(0.3)
            self.param_layout.addRow("Probabilidad de arista:", self.p_spin)
            
        elif graph_type == 1:  # Complete
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 100)
            self.n_spin.setValue(5)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
        elif graph_type == 2:  # Bipartite
            self.n1_spin = QSpinBox()
            self.n1_spin.setRange(1, 100)
            self.n1_spin.setValue(3)
            self.param_layout.addRow("Nodos conjunto 1:", self.n1_spin)
            
            self.n2_spin = QSpinBox()
            self.n2_spin.setRange(1, 100)
            self.n2_spin.setValue(3)
            self.param_layout.addRow("Nodos conjunto 2:", self.n2_spin)
            
        elif graph_type == 3:  # Tree
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 1000)
            self.n_spin.setValue(10)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
        elif graph_type in [4, 5]:  # Cycle, Path
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 1000)
            self.n_spin.setValue(8)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
        elif graph_type in [6, 7]:  # Wheel, Star
            self.n_spin = QSpinBox()
            self.n_spin.setRange(3, 1000)
            self.n_spin.setValue(8)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
        elif graph_type == 8:  # Grid
            self.rows_spin = QSpinBox()
            self.rows_spin.setRange(2, 50)
            self.rows_spin.setValue(5)
            self.param_layout.addRow("Filas:", self.rows_spin)
            
            self.cols_spin = QSpinBox()
            self.cols_spin.setRange(2, 50)
            self.cols_spin.setValue(5)
            self.param_layout.addRow("Columnas:", self.cols_spin)
            
        elif graph_type == 9:  # Regular
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 1000)
            self.n_spin.setValue(10)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
            self.d_spin = QSpinBox()
            self.d_spin.setRange(1, 20)
            self.d_spin.setValue(3)
            self.param_layout.addRow("Grado de cada nodo:", self.d_spin)
            
        elif graph_type == 10:  # Barabási-Albert
            self.n_spin = QSpinBox()
            self.n_spin.setRange(2, 1000)
            self.n_spin.setValue(20)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
            self.m_spin = QSpinBox()
            self.m_spin.setRange(1, 10)
            self.m_spin.setValue(2)
            self.param_layout.addRow("Aristas por nodo:", self.m_spin)
            
        elif graph_type == 11:  # Watts-Strogatz
            self.n_spin = QSpinBox()
            self.n_spin.setRange(4, 1000)
            self.n_spin.setValue(20)
            self.param_layout.addRow("Número de nodos:", self.n_spin)
            
            self.k_spin = QSpinBox()
            self.k_spin.setRange(2, 20)
            self.k_spin.setValue(4)
            self.param_layout.addRow("Vecinos cercanos:", self.k_spin)
            
            self.p_spin = QDoubleSpinBox()
            self.p_spin.setRange(0.0, 1.0)
            self.p_spin.setSingleStep(0.1)
            self.p_spin.setValue(0.3)
            self.param_layout.addRow("Probabilidad de reconexión:", self.p_spin)
    
    def generate(self):
        import random
        graph_type = self.graph_types.currentIndex()
        nodes = []
        edges = []
        
        try:
            if graph_type == 0:  # Random
                n = self.n_spin.value()
                p = self.p_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                for i in range(n):
                    for j in range(i + 1, n):
                        if random.random() < p:
                            edges.append((nodes[i], nodes[j], random.uniform(1, 10)))
            
            elif graph_type == 1:  # Complete
                n = self.n_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                for i in range(n):
                    for j in range(i + 1, n):
                        edges.append((nodes[i], nodes[j], random.uniform(1, 10)))
            
            elif graph_type == 2:  # Bipartite
                n1 = self.n1_spin.value()
                n2 = self.n2_spin.value()
                nodes = [f"A{i}" for i in range(n1)] + [f"B{i}" for i in range(n2)]
                for i in range(n1):
                    for j in range(n2):
                        edges.append((f"A{i}", f"B{j}", random.uniform(1, 10)))
            
            elif graph_type == 3:  # Tree
                n = self.n_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                for i in range(1, n):
                    parent = random.randint(0, i - 1)
                    edges.append((nodes[parent], nodes[i], random.uniform(1, 10)))
            
            elif graph_type == 4:  # Cycle
                n = self.n_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                for i in range(n):
                    edges.append((nodes[i], nodes[(i + 1) % n], random.uniform(1, 10)))
            
            elif graph_type == 5:  # Path
                n = self.n_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                for i in range(n - 1):
                    edges.append((nodes[i], nodes[i + 1], random.uniform(1, 10)))
            
            elif graph_type == 6:  # Wheel
                n = self.n_spin.value()
                nodes = ["Center"] + [f"N{i}" for i in range(n - 1)]
                for i in range(1, n):
                    edges.append(("Center", nodes[i], random.uniform(1, 10)))
                for i in range(1, n):
                    edges.append((nodes[i], nodes[(i % (n - 1)) + 1], random.uniform(1, 10)))
            
            elif graph_type == 7:  # Star
                n = self.n_spin.value()
                nodes = ["Center"] + [f"N{i}" for i in range(n - 1)]
                for i in range(1, n):
                    edges.append(("Center", nodes[i], random.uniform(1, 10)))
            
            elif graph_type == 8:  # Grid
                rows = self.rows_spin.value()
                cols = self.cols_spin.value()
                nodes = [f"N{i}_{j}" for i in range(rows) for j in range(cols)]
                for i in range(rows):
                    for j in range(cols):
                        if j < cols - 1:
                            edges.append((f"N{i}_{j}", f"N{i}_{j+1}", random.uniform(1, 10)))
                        if i < rows - 1:
                            edges.append((f"N{i}_{j}", f"N{i+1}_{j}", random.uniform(1, 10)))
            
            elif graph_type == 9:  # Regular
                n = self.n_spin.value()
                d = self.d_spin.value()
                if n * d % 2 != 0:
                    QMessageBox.warning(self, "Error", "n*d debe ser par para un grafo regular")
                    return
                nodes = [f"N{i}" for i in range(n)]
                # Simple regular graph construction
                for i in range(n):
                    for j in range(1, d // 2 + 1):
                        target = (i + j) % n
                        if (nodes[i], nodes[target]) not in [(e[0], e[1]) for e in edges]:
                            edges.append((nodes[i], nodes[target], random.uniform(1, 10)))
            
            elif graph_type == 10:  # Barabási-Albert
                n = self.n_spin.value()
                m = self.m_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                # Start with m nodes fully connected
                for i in range(m):
                    for j in range(i + 1, m):
                        edges.append((nodes[i], nodes[j], random.uniform(1, 10)))
                # Add remaining nodes with preferential attachment
                degrees = {node: 0 for node in nodes[:m]}
                for i in range(m):
                    for j in range(i + 1, m):
                        degrees[nodes[i]] += 1
                        degrees[nodes[j]] += 1
                
                for i in range(m, n):
                    targets = []
                    total_degree = sum(degrees.values())
                    for _ in range(min(m, i)):
                        r = random.random() * total_degree
                        cumsum = 0
                        for node, deg in degrees.items():
                            cumsum += deg
                            if cumsum >= r and node not in targets:
                                targets.append(node)
                                break
                    degrees[nodes[i]] = 0
                    for target in targets:
                        edges.append((nodes[i], target, random.uniform(1, 10)))
                        degrees[nodes[i]] += 1
                        degrees[target] += 1
            
            elif graph_type == 11:  # Watts-Strogatz
                n = self.n_spin.value()
                k = self.k_spin.value()
                p = self.p_spin.value()
                nodes = [f"N{i}" for i in range(n)]
                # Create ring lattice
                for i in range(n):
                    for j in range(1, k // 2 + 1):
                        target = (i + j) % n
                        edges.append((nodes[i], nodes[target], random.uniform(1, 10)))
                # Rewire edges
                new_edges = []
                for edge in edges:
                    if random.random() < p:
                        new_target = random.choice([node for node in nodes if node != edge[0]])
                        new_edges.append((edge[0], new_target, edge[2]))
                    else:
                        new_edges.append(edge)
                edges = new_edges
            
            self.result = {'nodes': nodes, 'edges': edges}
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar grafo:\n{str(e)}")


# ============================================================================
# DIALOGO DE ANALISIS DE GRAFO
# ============================================================================

class GraphAnalysisDialog(QDialog):
    """Dialog showing graph analysis and properties"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Análisis de Grafo")
        self.setMinimumSize(600, 500)
        self.canvas = canvas
        self.init_ui()
        self.analyze()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs for different analyses
        tabs = QTabWidget()
        
        # Basic properties
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        self.basic_text = QTextEdit()
        self.basic_text.setReadOnly(True)
        basic_layout.addWidget(self.basic_text)
        tabs.addTab(basic_tab, "Propiedades Básicas")
        
        # Centrality measures
        centrality_tab = QWidget()
        centrality_layout = QVBoxLayout(centrality_tab)
        self.centrality_table = QTableWidget()
        centrality_layout.addWidget(self.centrality_table)
        tabs.addTab(centrality_tab, "Centralidad")
        
        # Degree distribution
        degree_tab = QWidget()
        degree_layout = QVBoxLayout(degree_tab)
        self.degree_table = QTableWidget()
        degree_layout.addWidget(self.degree_table)
        tabs.addTab(degree_tab, "Distribución de Grados")
        
        # Components
        components_tab = QWidget()
        components_layout = QVBoxLayout(components_tab)
        self.components_text = QTextEdit()
        self.components_text.setReadOnly(True)
        components_layout.addWidget(self.components_text)
        tabs.addTab(components_tab, "Componentes")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def analyze(self):
        if not self.canvas.nodes:
            self.basic_text.setText("No hay nodos en el grafo.")
            return
        
        # Basic properties
        n_nodes = len(self.canvas.nodes)
        n_edges = len(self.canvas.edges)
        
        # Calculate degrees
        degrees = {node_id: 0 for node_id in self.canvas.nodes}
        for edge in self.canvas.edges.values():
            degrees[edge.source] += 1
            degrees[edge.target] += 1
        
        avg_degree = sum(degrees.values()) / n_nodes if n_nodes > 0 else 0
        max_degree = max(degrees.values()) if degrees else 0
        min_degree = min(degrees.values()) if degrees else 0
        
        # Density
        max_edges = n_nodes * (n_nodes - 1) / 2
        density = n_edges / max_edges if max_edges > 0 else 0
        
        # Basic properties text
        basic_info = f"""
            Número de nodos: {n_nodes}
            Número de aristas: {n_edges}
            Densidad: {density:.4f}

            Grado promedio: {avg_degree:.2f}
            Grado máximo: {max_degree}
            Grado mínimo: {min_degree}
            """
        
        # Check if NetworkX is available for advanced analysis
        if HAS_NETWORKX:
            G = self.build_networkx_graph()
            
            # Diameter and radius
            if nx.is_connected(G):
                diameter = nx.diameter(G)
                radius = nx.radius(G)
                basic_info += f"\nDiámetro: {diameter}\nRadio: {radius}"
            else:
                basic_info += "\n\nGrafo no conexo"
            
            # Clustering coefficient
            clustering = nx.average_clustering(G)
            basic_info += f"\nCoeficiente de clustering promedio: {clustering:.4f}"
            
            # Centrality measures
            self.calculate_centrality(G)
            
            # Components
            self.analyze_components(G)
        else:
            basic_info += "\n\n(Instale NetworkX para análisis avanzado)"
        
        self.basic_text.setText(basic_info)
        
        # Degree distribution
        self.show_degree_distribution(degrees)
    
    def build_networkx_graph(self):
        import networkx as nx
        G = nx.Graph()
        for node_id in self.canvas.nodes:
            G.add_node(node_id)
        for edge in self.canvas.edges.values():
            G.add_edge(edge.source, edge.target, weight=edge.weight)
        return G
    
    def calculate_centrality(self, G):
        # Degree centrality
        degree_cent = nx.degree_centrality(G)
        
        # Betweenness centrality
        betweenness_cent = nx.betweenness_centrality(G)
        
        # Closeness centrality
        closeness_cent = nx.closeness_centrality(G)
        
        # Setup table
        self.centrality_table.setColumnCount(4)
        self.centrality_table.setHorizontalHeaderLabels([
            "Nodo", "Grado", "Intermediación", "Cercanía"
        ])
        self.centrality_table.setRowCount(len(self.canvas.nodes))
        
        sorted_nodes = sorted(self.canvas.nodes.items(), key=lambda item: item[1].label)

        for i, (node_id, node) in enumerate(sorted_nodes):
            self.centrality_table.setItem(i, 0, QTableWidgetItem(node.label))
            self.centrality_table.setItem(i, 1, QTableWidgetItem(f"{degree_cent[node_id]:.4f}"))
            self.centrality_table.setItem(i, 2, QTableWidgetItem(f"{betweenness_cent[node_id]:.4f}"))
            self.centrality_table.setItem(i, 3, QTableWidgetItem(f"{closeness_cent[node_id]:.4f}"))
        
        self.centrality_table.resizeColumnsToContents()
    
    def show_degree_distribution(self, degrees):
        # Count degree frequencies
        degree_freq = {}
        for deg in degrees.values():
            degree_freq[deg] = degree_freq.get(deg, 0) + 1
        
        self.degree_table.setColumnCount(2)
        self.degree_table.setHorizontalHeaderLabels(["Grado", "Frecuencia"])
        self.degree_table.setRowCount(len(degree_freq))
        
        sorted_freq = sorted(degree_freq.items())

        for i, (deg, freq) in enumerate(sorted_freq):
            self.degree_table.setItem(i, 0, QTableWidgetItem(str(deg)))
            self.degree_table.setItem(i, 1, QTableWidgetItem(str(freq)))
        
        self.degree_table.resizeColumnsToContents()
    
    def analyze_components(self, G):
        components = list(nx.connected_components(G))
        
        text = f"Número de componentes conexas: {len(components)}\n\n"
        
        sorted_components = sorted(components, key=lambda comp: (len(comp), sorted(self.canvas.nodes[n].label for n in comp)))

        for i, comp in enumerate(sorted_components, 1):
            labels = sorted([self.canvas.nodes[nid].label for nid in comp])
            text += f"Componente {i} ({len(comp)} nodos): {', '.join(labels)}\n"
        
        self.components_text.setText(text)


# ============================================================================
# ATAJOS DE TECLADO
# ============================================================================

class ShortcutsDialog(QDialog):
    """Dialog showing keyboard shortcuts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atajos de Teclado")
        self.setMinimumSize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setHtml("""
        <h2>Atajos de Teclado</h2>
        
        <h3>Archivo</h3>
        <ul>
            <li><b>Ctrl+N</b> - Nuevo grafo</li>
            <li><b>Ctrl+O</b> - Abrir grafo</li>
            <li><b>Ctrl+S</b> - Guardar grafo</li>
            <li><b>Ctrl+Q</b> - Salir</li>
        </ul>
        
        <h3>Edición</h3>
        <ul>
            <li><b>Ctrl+Z</b> - Deshacer</li>
            <li><b>Ctrl+Y</b> - Rehacer</li>
            <li><b>Delete / Backspace</b> - Eliminar selección</li>
            <li><b>Ctrl+A</b> - Seleccionar todo</li>
        </ul>
        
        <h3>Vista</h3>
        <ul>
            <li><b>Ctrl++</b> - Acercar zoom</li>
            <li><b>Ctrl+-</b> - Alejar zoom</li>
            <li><b>Ctrl+0</b> - Restablecer zoom</li>
            <li><b>Rueda del ratón</b> - Zoom</li>
            <li><b>Botón central + arrastrar</b> - Pan</li>
        </ul>
        
        <h3>Nodos y Aristas</h3>
        <ul>
            <li><b>Clic izquierdo</b> - Crear nodo (espacio vacío) / Seleccionar</li>
            <li><b>Clic derecho</b> - Menú contextual</li>
            <li><b>Arrastrar</b> - Mover nodo</li>
            <li><b>Ctrl+Clic</b> - Selección múltiple</li>
        </ul>
        
        <h3>Algoritmos</h3>
        <ul>
            <li><b>F5</b> - Ejecutar BFS</li>
            <li><b>F6</b> - Ejecutar DFS</li>
            <li><b>F7</b> - Ejecutar Dijkstra</li>
            <li><b>F8</b> - Ejecutar Kruskal</li>
        </ul>
        """)
        
        layout.addWidget(shortcuts_text)
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ============================================================================
# CONTROL DE ANIMACION
# ============================================================================

class AnimationController:
    """Controls step-by-step algorithm animation"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.steps = []
        self.current_step = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
        self.speed = 1000  # ms per step
    
    def set_steps(self, steps):
        """Set animation steps"""
        self.steps = steps
        self.current_step = 0
        # Auto stop any running timer and prepare UI if present
        if self.timer.isActive():
            self.timer.stop()
    
    def start(self):
        """Start animation"""
        if self.steps:
            self.timer.start(self.speed)

    def pause(self):
        """Pause animation without resetting current step"""
        if self.timer.isActive():
            self.timer.stop()

    def is_running(self) -> bool:
        """Return whether the animation timer is active"""
        return self.timer.isActive()
    
    def stop(self):
        """Stop animation"""
        self.timer.stop()
    
    def next_step(self):
        """Execute next step"""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.canvas.highlight_nodes(step.get('nodes', []))
            self.canvas.highlight_edges(step.get('edges', []))
            self.current_step += 1
        else:
            self.stop()
            # Optionally clear highlights after animation
            # self.canvas.clear_highlights()
        # Update log if parent has method
        try:
            if hasattr(self.canvas.parent(), 'log'):
                self.canvas.parent().log(f"Animación paso {self.current_step}/{len(self.steps)}")
        except Exception:
            pass
    
    def set_speed(self, speed_ms):
        """Set animation speed in milliseconds"""
        self.speed = speed_ms
        if self.timer.isActive():
            self.timer.setInterval(speed_ms)


# ============================================================================
# 3D VISUALIZACION
# ============================================================================

def launch_3d_view(nodes_data, edges_data, lighting, shadows, sky):
    """Vista 3D mejorada con Ursina.

    Mejoras añadidas:
    - Normalización y centrado del grafo para que siempre quede dentro del campo de la cámara.
    - Escalado en función del span máximo en X/Y (bounding box) para ocupar un volumen manejable.
    - Posicionamiento automático de la cámara según el tamaño del grafo.
    - Etiquetas adaptativas por nodo y pesos centrados en cada arista.
    - Manejo de caso de grafo vacío (no debería lanzarse, pero se protege).
    """
    if not HAS_URSINA:
        return

    if not nodes_data:
        return

    # Intentar layout 3D real con spring_layout dim=3 si NetworkX disponible
    transformed_positions = {}
    target_span = 10.0
    if HAS_NETWORKX:
        try:
            import networkx as nx
            G = nx.Graph()
            for nid in nodes_data.keys():
                G.add_node(nid)
            for ed in edges_data.values():
                G.add_edge(ed['source'], ed['target'])
            pos3d = nx.spring_layout(G, dim=3, seed=42)
            xs = [p[0] for p in pos3d.values()]; ys = [p[1] for p in pos3d.values()]; zs = [p[2] for p in pos3d.values()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)
            span = max(max_x-min_x, max_y-min_y, max_z-min_z) or 1.0
            scale = target_span / span
            cx = (min_x + max_x) / 2.0; cy = (min_y + max_y) / 2.0; cz = (min_z + max_z) / 2.0
            for nid, p in pos3d.items():
                transformed_positions[nid] = ((p[0]-cx)*scale, (p[1]-cy)*scale, (p[2]-cz)*scale)
        except Exception:
            transformed_positions = {}
    if not transformed_positions:
        # Fallback a proyección 2D original en plano XZ
        xs = [nd['pos'][0] for nd in nodes_data.values()]
        ys = [nd['pos'][1] for nd in nodes_data.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max_x - min_x if max_x > min_x else 1.0
        span_y = max_y - min_y if max_y > min_y else 1.0
        max_span = max(span_x, span_y)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        scale_factor = target_span / max_span if max_span > 0 else 1.0
        for nid, nd in nodes_data.items():
            ox, oy = nd['pos']
            tx = (ox - center_x) * scale_factor
            ty = (oy - center_y) * scale_factor
            transformed_positions[nid] = (tx, 0.0, ty)

    # Ajuste cámara en función del tamaño
    approx_radius = target_span / 2.0
    cam_distance = approx_radius * 1.8 + 4  # distancia base + factor tamaño

    app = Ursina()
    window.title = 'Grafos - Vista 3D'
    window.fullscreen = False
    window.exit_button.visible = False
    window.fps_counter.enabled = False

    # Iluminación / ambiente
    if lighting:
        DirectionalLight(y=3, z=4, shadows=shadows, rotation=(45, 135, 0))
        AmbientLight(color=color.rgb(110, 110, 130))
    if sky:
        Sky(texture='sky_sunset')

    node_entities = {}

    class Node3D(Entity):
        def __init__(self, nid, data):
            pos3d = transformed_positions[nid]
            col = color.rgb(*data['color'])
            # Escala base proporcional al size original (20 -> ~0.7)
            node_scale = data.get('size', 20.0) / 28.0
            super().__init__(model='sphere', color=col, position=pos3d, scale=node_scale, collider='sphere')
            self.nid = nid
            self.base_color = col
            Text(text=data['label'], position=self.position + Vec3(0, node_scale*1.25, 0), scale=1.5, billboard=True, color=color.white)
        def input(self, key):
            if key == 'left mouse down' and mouse.hovered_entity == self:
                self.color = color.yellow
            if key == 'left mouse up' and self.color == color.yellow:
                self.color = self.base_color

    # Crear nodos
    for nid, nd in nodes_data.items():
        node_entities[nid] = Node3D(nid, nd)

    # Crear aristas
    for ed in edges_data.values():
        s = ed['source']; t = ed['target']
        if s not in node_entities or t not in node_entities:
            continue
        sp = node_entities[s].position
        tp = node_entities[t].position
        direction = tp - sp
        dist = direction.length()
        if dist <= 0.0001:
            continue
        mid = (sp + tp) / 2
        edge_col = color.rgb(*ed['color'])
        # Usamos cube estrecho como barra
        thickness = max(0.04, 0.04 * (target_span / 10.0))
        cyl = Entity(model='cube', color=edge_col, position=mid, scale=(thickness, thickness, dist), collider=None)
        cyl.look_at(tp)
        # Peso centrado sobre la arista
        Text(text=f"{ed.get('weight', 1):.2f}", position=mid + Vec3(0, thickness*3, 0), scale=1, billboard=True, color=color.white)
        # Flecha si dirigida
        if ed.get('directed'):
            arr_dir = direction.normalized()
            arrow_pos = tp - arr_dir * 0.15
            cone = Entity(model='cone', color=edge_col, position=arrow_pos, scale=thickness*4)
            cone.look_at(tp + arr_dir)

    class CameraController(Entity):
        def __init__(self):
            super().__init__()
            self.rotation_speed = 60
            self.move_speed = 5
        def update(self):
            if held_keys['right mouse']:
                camera.rotation_y += mouse.velocity[0] * self.rotation_speed
                camera.rotation_x -= mouse.velocity[1] * self.rotation_speed
                camera.rotation_x = clamp(camera.rotation_x, -80, 80)
            mv = Vec3(0, 0, 0)
            if held_keys['w']: mv += camera.forward
            if held_keys['s']: mv -= camera.forward
            if held_keys['a']: mv -= camera.right
            if held_keys['d']: mv += camera.right
            if held_keys['q']: mv += Vec3(0, 1, 0)
            if held_keys['e']: mv -= Vec3(0, 1, 0)
            if mv.length() > 0: camera.position += mv.normalized() * self.move_speed * time.dt
        def input(self, key):
            if key == 'scroll up': camera.position += camera.forward * 0.5
            if key == 'scroll down': camera.position -= camera.forward * 0.5

    CameraController()
    camera.position = Vec3(0, approx_radius * 0.6, -cam_distance)
    camera.rotation_x = 25
    app.run()


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Mejor soporte de alto DPI (evita avisos de Qt y mejora el escalado en Windows)
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName("Grafos GUI")
    app.setOrganizationName("GraphGUI")

    # Intentar cargar un icono llamado 'Grafos.ico' situado junto al script
    try:
        icon_path = Path(__file__).with_name('Grafos.ico')
        if not icon_path.exists():
            # intentar también en el directorio de trabajo
            icon_path = Path.cwd() / 'Grafos.ico'
        if icon_path.exists():
            app_icon = QIcon(str(icon_path))
            app.setWindowIcon(app_icon)
    except Exception:
        # no bloquear la ejecución por problemas con el icono
        pass

    window = MainWindow()
    # establecer también el icono en la ventana principal si fue cargado
    try:
        if 'app_icon' in locals():
            window.setWindowIcon(app_icon)
    except Exception:
        pass

    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
