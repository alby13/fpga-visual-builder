# FPGA Builder Build 19, August 11, 2024.

import json
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QGraphicsScene, QGraphicsView, 
                             QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QInputDialog, QGraphicsTextItem, 
                             QGraphicsRectItem, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPen, QColor, QBrush, QPainter, QPixmap, QPainterPath

GRID_SIZE = 20

class Pin(QGraphicsRectItem):
    def __init__(self, parent, x, y):
        super().__init__(parent)
        self.setRect(x - 2, y - 2, 4, 4)
        self.setBrush(QBrush(Qt.black))
        self.setFlag(QGraphicsItem.ItemIsSelectable)

class FPGAComponent(QGraphicsItem):
    def __init__(self, x, y, width, height, label="", pin_count=8, pin_orientation='left-right'):
        super().__init__()
        self.setPos(x, y)
        self.width = width
        self.height = height
        self.label = label
        self.pin_count = pin_count
        self.pin_orientation = pin_orientation
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.rotation_angle = 0
        self.text_item = QGraphicsTextItem(self.label, self)
        self.text_item.setPos(5, 5)
        self.pins = []
        self.create_pins()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(Qt.lightGray))
        painter.drawRect(0, 0, self.width, self.height)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            new_pos.setX(round(new_pos.x() / GRID_SIZE) * GRID_SIZE)
            new_pos.setY(round(new_pos.y() / GRID_SIZE) * GRID_SIZE)
            self.update_connections()
            return new_pos
        return super().itemChange(change, value)

    def setLabel(self, label):
        self.label = label
        self.text_item.setPlainText(self.label)

    def create_pins(self):
        if self.pin_orientation == 'left-right':
            pin_spacing = self.height / (self.pin_count + 1)
            for i in range(self.pin_count):
                pin = Pin(self, 0, (i + 1) * pin_spacing)
                self.pins.append(pin)
                pin = Pin(self, self.width, (i + 1) * pin_spacing)
                self.pins.append(pin)
        else:
            pin_spacing = self.width / (self.pin_count + 1)
            for i in range(self.pin_count):
                pin = Pin(self, (i + 1) * pin_spacing, 0)
                self.pins.append(pin)
                pin = Pin(self, (i + 1) * pin_spacing, self.height)
                self.pins.append(pin)

    def rotate_component(self):
        self.rotation_angle += 90
        if self.rotation_angle >= 360:
            self.rotation_angle = 0
        self.setRotation(self.rotation_angle)
        self.update_connections()

    def update_connections(self):
        for item in self.scene().items():
            if isinstance(item, Connection):
                item.updatePosition()

class Connection(QGraphicsPathItem):
    def __init__(self, source, target):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.updatePosition()

    def updatePosition(self):
        source_pos = self.source.scenePos()
        target_pos = self.target.scenePos()
        x1, y1 = source_pos.x(), source_pos.y()
        x2, y2 = target_pos.x(), target_pos.y()
        if x1 == x2:
            path = QPainterPath()
            path.moveTo(x1, min(y1, y2))
            path.lineTo(x2, max(y1, y2))
            self.setPath(path)
        elif y1 == y2:
            path = QPainterPath()
            path.moveTo(min(x1, x2), y1)
            path.lineTo(max(x1, x2), y2)
            self.setPath(path)
        else:
            lines = []
            if x1 < x2:
                lines.append((x1, y1, x1, y2))
                lines.append((x1, y2, x2, y2))
            else:
                lines.append((x1, y1, x2, y1))
                lines.append((x2, y1, x2, y2))
            self.setPath(self.create_path(lines))

    def create_path(self, lines):
        path = QPainterPath()
        for line in lines:
            if path.isEmpty():
                path.moveTo(line[0], line[1])
            path.lineTo(line[2], line[3])
        return path

class GraphicsView(QGraphicsView):
    def __init__(self, scene, main_window):
        super().__init__(scene)
        self.main_window = main_window
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self.main_window.connecting:
            item = self.itemAt(event.pos())
            if isinstance(item, Pin):
                if self.main_window.connection_source is None:
                    self.main_window.connection_source = item
                else:
                    if self.main_window.connection_source != item and self.main_window.connection_source.parentItem() != item.parentItem():
                        connection = Connection(self.main_window.connection_source, item)
                        self.scene().addItem(connection)
                        self.main_window.undo_stack.append({"action": "add_connection", "item": connection})
                        self.main_window.redo_stack = []
                        self.main_window.toggle_connection_mode()
                    else:
                        QMessageBox.warning(self.main_window, "Invalid Connection", "Cannot connect the same pin or pins from the same component.")
                        self.main_window.connection_source = None
        elif self.main_window.rotating:
            item = self.itemAt(event.pos())
            if isinstance(item, FPGAComponent):
                item.rotate_component()
        elif event.button() == Qt.RightButton:
            item = self.itemAt(event.pos())
            if isinstance(item, FPGAComponent):
                self.delete_component(item)
            elif isinstance(item, Connection):
                self.delete_connection(item)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.main_window.zoom_in()
        else:
            self.main_window.zoom_out()
        event.accept()

    def delete_component(self, component):
        connections = []
        for item in self.scene().items():
            if isinstance(item, Connection):
                if item.source.parentItem() == component or item.target.parentItem() == component:
                    connections.append(item)
                    self.scene().removeItem(item)
        self.scene().removeItem(component)
        self.main_window.undo_stack.append({"action": "delete_component", "item": component, "connections": connections})
        self.main_window.redo_stack = []

    def delete_connection(self, connection):
        self.scene().removeItem(connection)
        self.main_window.undo_stack.append({"action": "delete_connection", "item": connection})
        self.main_window.redo_stack = []

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FPGA Builder - Created by alby13")
        self.showMaximized()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)
        self.view.setSceneRect(0, 0, 2000, 1500)
        self.view.setRenderHint(QPainter.Antialiasing)
        
        self.draw_grid()
        
        button_layout = QHBoxLayout()
        
        self.add_component_button = QPushButton("Add Component")
        self.add_component_button.clicked.connect(self.add_component)
        button_layout.addWidget(self.add_component_button)

        self.add_connection_button = QPushButton("Add Connection")
        self.add_connection_button.clicked.connect(self.toggle_connection_mode)
        button_layout.addWidget(self.add_connection_button)

        self.rotate_component_button = QPushButton("Rotate Mode")
        self.rotate_component_button.clicked.connect(self.toggle_rotate_mode)
        button_layout.addWidget(self.rotate_component_button)

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        button_layout.addWidget(self.zoom_in_button)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        button_layout.addWidget(self.zoom_out_button)

        self.save_button = QPushButton("Save Image")
        self.save_button.clicked.connect(self.save_image)
        button_layout.addWidget(self.save_button)

        self.save_project_button = QPushButton("Save Project")
        self.save_project_button.clicked.connect(self.save_project)
        button_layout.addWidget(self.save_project_button)

        self.load_project_button = QPushButton("Load Project")
        self.load_project_button.clicked.connect(self.load_project)
        button_layout.addWidget(self.load_project_button)

        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.undo)
        button_layout.addWidget(self.undo_button)

        self.redo_button = QPushButton("Redo")
        self.redo_button.clicked.connect(self.redo)
        button_layout.addWidget(self.redo_button)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.view)
        
        self.connecting = False
        self.rotating = False
        self.connection_source = None
        self.undo_stack = []
        self.redo_stack = []
        
    def add_component(self):
        label, ok = QInputDialog.getText(self, "Component Label", "Enter label for the component:")
        if ok:
            pin_count, ok = QInputDialog.getInt(self, "Pin Count", "Enter number of pins:", 8, 2, 64)
            if ok:
                pin_orientation, ok = QInputDialog.getItem(self, "Pin Orientation", 
                                                           "Choose pin orientation:", 
                                                           ["left-right", "top-bottom"], 0, False)
                if ok:
                    component = FPGAComponent(0, 0, 100, 50, label, pin_count, pin_orientation)
                    self.scene.addItem(component)
                    self.undo_stack.append({"action": "add_component", "item": component})
                    self.redo_stack = []

    def toggle_connection_mode(self):
        if self.rotating:
            self.toggle_rotate_mode()
        self.connecting = not self.connecting
        if self.connecting:
            self.add_connection_button.setText("Cancel Connection")
            self.view.setCursor(Qt.CrossCursor)
        else:
            self.add_connection_button.setText("Add Connection")
            self.view.setCursor(Qt.ArrowCursor)
            self.connection_source = None

    def toggle_rotate_mode(self):
        if self.connecting:
            self.toggle_connection_mode()
        self.rotating = not self.rotating
        if self.rotating:
            self.rotate_component_button.setText("Cancel Rotate Mode")
            self.view.setCursor(Qt.CrossCursor)
        else:
            self.rotate_component_button.setText("Rotate Mode")
            self.view.setCursor(Qt.ArrowCursor)

    def zoom_in(self):
        self.view.scale(1.25, 1.25)

    def zoom_out(self):
        self.view.scale(0.8, 0.8)

    def draw_grid(self):
        rect = self.view.sceneRect()
        for x in range(int(rect.left()), int(rect.right()), GRID_SIZE):
            self.scene.addLine(x, rect.top(), x, rect.bottom(), QPen(Qt.lightGray))
        for y in range(int(rect.top()), int(rect.bottom()), GRID_SIZE):
            self.scene.addLine(rect.left(), y, rect.right(), y, QPen(Qt.lightGray))

    def save_image(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)")
        if filename:
            pixmap = QPixmap(self.scene.sceneRect().size().toSize())
            pixmap.fill(Qt.white)
            painter = QPainter(pixmap)
            self.scene.render(painter)
            painter.end()
            pixmap.save(filename)

    def undo(self):
        if self.undo_stack:
            action = self.undo_stack.pop()
            if action["action"] == "add_component":
                self.scene.removeItem(action["item"])
                self.redo_stack.append(action)
            elif action["action"] == "delete_component":
                self.scene.addItem(action["item"])
                for connection in action["connections"]:
                    self.scene.addItem(connection)
                self.redo_stack.append(action)
            elif action["action"] == "add_connection":
                self.scene.removeItem(action["item"])
                self.redo_stack.append(action)
            elif action["action"] == "delete_connection":
                self.scene.addItem(action["item"])
                self.redo_stack.append(action)

    def redo(self):
        if self.redo_stack:
            action = self.redo_stack.pop()
            if action["action"] == "add_component":
                self.scene.addItem(action["item"])
                self.undo_stack.append(action)
            elif action["action"] == "delete_component":
                self.scene.removeItem(action["item"])
                for connection in action["connections"]:
                    self.scene.removeItem(connection)
                self.undo_stack.append(action)
            elif action["action"] == "add_connection":
                self.scene.addItem(action["item"])
                self.undo_stack.append(action)
            elif action["action"] == "delete_connection":
                self.scene.removeItem(action["item"])
                self.undo_stack.append(action)

    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "FPGA Builder Project Files (*.fga);;All Files (*)")
        if filename:
            if not filename.endswith(".fga"):
                filename += ".fga"
            project_data = {
                "components": [],
                "connections": []
            }
            for item in self.scene.items():
                if isinstance(item, FPGAComponent):
                    component_data = {
                        "label": item.label,
                        "pin_count": item.pin_count,
                        "pin_orientation": item.pin_orientation,
                        "x": item.scenePos().x(),
                        "y": item.scenePos().y()
                    }
                    project_data["components"].append(component_data)
                elif isinstance(item, Connection):
                    connection_data = {
                        "source_label": item.source.parentItem().label,
                        "source_pin_index": item.source.parentItem().pins.index(item.source),
                        "target_label": item.target.parentItem().label,
                        "target_pin_index": item.target.parentItem().pins.index(item.target)
                    }
                    project_data["connections"].append(connection_data)
            with open(filename, "w") as file:
                json.dump(project_data, file)

    def load_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "FPGA Builder Project Files (*.fga);;All Files (*)")
        if filename:
            with open(filename, "r") as file:
                project_data = json.load(file)
            self.scene.clear()
            self.draw_grid()
            components = {}
            for component_data in project_data["components"]:
                component = FPGAComponent(component_data["x"], component_data["y"], 100, 50, component_data["label"], component_data["pin_count"], component_data["pin_orientation"])
                self.scene.addItem(component)
                components[component_data["label"]] = component
            for connection_data in project_data["connections"]:
                source_component = components[connection_data["source_label"]]
                target_component = components[connection_data["target_label"]]
                source_pin = source_component.pins[connection_data["source_pin_index"]]
                target_pin = target_component.pins[connection_data["target_pin_index"]]
                connection = Connection(source_pin, target_pin)
                self.scene.addItem(connection)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())