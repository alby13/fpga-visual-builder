# FPGA Builder Build 27, August 19, 2024.

import json
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QGraphicsScene, QGraphicsView, 
                             QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QInputDialog, QGraphicsTextItem, 
                             QGraphicsRectItem, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QFileDialog,
                             QDialog, QFormLayout, QComboBox, QSpinBox, QDialogButtonBox, QLineEdit)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPen, QColor, QBrush, QPainter, QPixmap, QPainterPath, QPolygonF, QFont

GRID_SIZE = 20

class ComponentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Component")
        
        layout = QFormLayout(self)
        
        self.label_edit = QLineEdit()
        layout.addRow("Component Label:", self.label_edit)
        
        self.component_type = QComboBox()
        self.component_type.addItems(["IC Chip", "Capacitor", "Resistor", "Crystal Oscillator", "Inductor", "Diode", "DIP Switch"])
        layout.addRow("Component Type:", self.component_type)
        
        self.chip_type = QComboBox()
        self.chip_type.addItems(["Regular", "Wide", "Square"])
        layout.addRow("Chip Type:", self.chip_type)
        
        self.pin_count = QSpinBox()
        self.pin_count.setRange(2, 64)
        self.pin_count.setValue(8)
        layout.addRow("Number of Pins:", self.pin_count)
        
        self.pin_orientation = QComboBox()
        self.pin_orientation.addItems(["left-right", "top-bottom", "all-sides"])
        layout.addRow("Pin Orientation:", self.pin_orientation)
        
        self.component_type.currentTextChanged.connect(self.update_form)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.update_form(self.component_type.currentText())

    def update_form(self, component_type):
        if component_type == "IC Chip":
            self.chip_type.setEnabled(True)
            self.pin_count.setEnabled(True)
            self.pin_orientation.setEnabled(True)
        elif component_type in ["Capacitor", "Resistor", "Inductor", "Diode"]:
            self.chip_type.setEnabled(False)
            self.pin_count.setValue(2)
            self.pin_count.setEnabled(False)
            self.pin_orientation.setCurrentText("left-right")
            self.pin_orientation.setEnabled(False)
        elif component_type == "Crystal Oscillator":
            self.chip_type.setEnabled(False)
            self.pin_count.setValue(4)
            self.pin_count.setEnabled(False)
            self.pin_orientation.setCurrentText("left-right")
            self.pin_orientation.setEnabled(False)
        elif component_type == "DIP Switch":
            self.chip_type.setEnabled(False)
            self.pin_count.setEnabled(True)
            self.pin_orientation.setCurrentText("top-bottom")
            self.pin_orientation.setEnabled(False)

    def get_data(self):
        return {
            "label": self.label_edit.text(),
            "component_type": self.component_type.currentText(),
            "chip_type": self.chip_type.currentText(),
            "pin_count": self.pin_count.value(),
            "pin_orientation": self.pin_orientation.currentText()
        }

class Pin(QGraphicsRectItem):
    def __init__(self, parent, x, y):
        super().__init__(parent)
        self.setRect(x - 2, y - 2, 4, 4)
        self.setBrush(QBrush(Qt.black))
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(1)  # Set the Z-value to be above components and connections
        self.parent_component = parent

    def scenePos(self):
        return self.parent_component.scenePos() + self.pos()

class FPGAComponent(QGraphicsItem):
    def __init__(self, x, y, width, height, label="", pin_count=8, pin_orientation='left-right', component_type="IC Chip"):
        super().__init__()
        self.setPos(x, y)
        self.width = width
        self.height = height
        self.label = label
        self.pin_count = pin_count
        self.pin_orientation = pin_orientation
        self.component_type = component_type
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)  # Set the Z-value to be above connections
        self.rotation_angle = 0
        self.pins = []
        self.create_pins()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black, 1))
        #painter.setBrush(QBrush(Qt.lightGray))
        #painter.drawRect(0, 0, self.width, self.height)
    
        if self.component_type == "Capacitor":
            painter.setBrush(QBrush(QColor(173, 216, 230)))  # Light blue

            # Draw the cylinder body
            body_height = int(self.height * 0.8)
            body_top = 0
            painter.drawRect(0, body_top, self.width, body_height)
            
            # Draw the curved top
            painter.drawArc(0, body_top, self.width, int(self.height * 0.2), 0, 180 * 16)
            
            # Draw the curved bottom
            painter.drawArc(0, body_top + body_height - int(self.height * 0.2), 
                            self.width, int(self.height * 0.2), 180 * 16, 180 * 16)
            
            # Draw the pins
            painter.setBrush(QBrush(Qt.black))
            pin_width = int(self.width * 0.2)
            pin_height = int(self.height * 0.2)
            painter.drawRect(int(self.width * 0.2), self.height - pin_height, pin_width, pin_height)
            painter.drawRect(int(self.width * 0.6), self.height - pin_height, pin_width, pin_height)
            
        elif self.component_type == "Resistor":
            painter.setBrush(QBrush(Qt.lightGray))
            painter.drawRect(0, int(self.height * 0.25), self.width, int(self.height * 0.5))
            painter.drawLine(0, int(self.height/2), int(self.width), int(self.height/2))
        elif self.component_type == "Inductor":
            painter.setBrush(QBrush(Qt.lightGray))
            path = QPainterPath()
            path.moveTo(0, int(self.height/2))
            for i in range(4):
                path.arcTo(int(i * self.width/4), int(self.height/4), 
                           int(self.width/4), int(self.height/2), 180, -180)
            path.lineTo(self.width, int(self.height/2))
            painter.drawPath(path)
        elif self.component_type == "Crystal Oscillator":
            painter.setBrush(QBrush(Qt.lightGray))
            painter.drawRect(int(self.width/4), 0, int(self.width/2), int(self.height))
        elif self.component_type == "Diode":
            painter.setBrush(QBrush(Qt.lightGray))
            painter.drawLine(0, int(self.height/2), int(self.width), int(self.height/2))
            painter.drawPolygon(QPolygonF([
                QPointF(self.width/2, 0),
                QPointF(self.width/2, self.height),
                QPointF(self.width, self.height/2)
            ]))
        elif self.component_type == "DIP Switch":
            switch_width = self.width / self.pin_count
            for i in range(self.pin_count // 2):
                painter.drawRect(int(i * switch_width * 2), 0, int(switch_width), int(self.height))
        else:  # IC Chip
            painter.setBrush(QBrush(Qt.lightGray))
            painter.drawRect(0, 0, self.width, self.height)

        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 8))
        
        painter.drawText(QRectF(0, 0, self.width, self.height), Qt.AlignCenter, self.label)


    def create_pins(self):
        # pins_per_side = max(1, self.pin_count // 4)  # Ensure at least 1 pin per side
        pins_per_side = self.pin_count // 2  # Divide total pins by 2 for each side

        if self.pin_orientation == 'left-right':
            pin_spacing = self.height / (self.pin_count // 2 + 1)
            for i in range(self.pin_count // 2):
                pin = Pin(self, 0, (i + 1) * pin_spacing)
                self.pins.append(pin)
                pin = Pin(self, self.width, (i + 1) * pin_spacing)
                self.pins.append(pin)
        elif self.pin_orientation == 'top-bottom':
            pin_spacing = self.width / (self.pin_count // 2 + 1)
            for i in range(self.pin_count // 2):
                pin = Pin(self, (i + 1) * pin_spacing, 0)
                self.pins.append(pin)
                pin = Pin(self, (i + 1) * pin_spacing, self.height)
                self.pins.append(pin)
        else:  # all-sides
            pins_per_side = max(1, self.pin_count // 4)  # Divide total pins by 4 for each side
            extra_pins = self.pin_count % 4
        
            # Top side
            h_spacing = self.width / (pins_per_side + 1)
            for i in range(pins_per_side + extra_pins):
                pin = Pin(self, (i + 1) * h_spacing, 0)
                self.pins.append(pin)
    
            # Bottom side
            for i in range(pins_per_side):
                pin = Pin(self, (i + 1) * h_spacing, self.height)
                self.pins.append(pin)
    
            # Left side
            v_spacing = self.height / (pins_per_side + 1)
            for i in range(pins_per_side):
                pin = Pin(self, 0, (i + 1) * v_spacing)
                self.pins.append(pin)
    
            # Right side
            for i in range(pins_per_side):
                pin = Pin(self, self.width, (i + 1) * v_spacing)
                self.pins.append(pin)
        

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
        self.setZValue(-1)  # Set the Z-value to be below components
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
        self.connection_start = None
        self.temp_connection = None

    def mousePressEvent(self, event):
        if self.main_window.connecting:
            item = self.itemAt(event.pos())
            if isinstance(item, Pin):
                if self.connection_start is None:
                    self.connection_start = item
                    self.connection_start.setBrush(QBrush(Qt.red))
                else:
                    if self.connection_start != item and self.connection_start.parent_component != item.parent_component:
                        connection = Connection(self.connection_start, item)
                        self.scene().addItem(connection)
                        connection.setZValue(-1)  # Ensure the connection is above the grid but below components
                        self.main_window.undo_stack.append({"action": "add_connection", "item": connection})
                        self.main_window.redo_stack = []
                        self.connection_start.setBrush(QBrush(Qt.black))
                        self.connection_start = None
                        self.main_window.toggle_connection_mode()
                    else:
                        self.connection_start.setBrush(QBrush(Qt.black))
                        self.connection_start = None
            else:
                if self.connection_start:
                    self.connection_start.setBrush(QBrush(Qt.black))
                    self.connection_start = None
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

    def mouseMoveEvent(self, event):
        if self.main_window.connecting and self.connection_start:
            end_item = self.itemAt(event.pos())
            if isinstance(end_item, Pin) and end_item.parent_component != self.connection_start.parent_component:
                end_pos = end_item.scenePos()
            else:
                end_pos = self.mapToScene(event.pos())
            
            if self.temp_connection:
                self.scene().removeItem(self.temp_connection)
            
            self.temp_connection = QGraphicsLineItem(
                self.connection_start.scenePos().x(),
                self.connection_start.scenePos().y(),
                end_pos.x(),
                end_pos.y()
            )
            self.temp_connection.setPen(QPen(Qt.red, 2, Qt.DashLine))
            self.temp_connection.setZValue(-1)  # Ensure the temporary connection is below components
            self.scene().addItem(self.temp_connection)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.main_window.connecting and self.temp_connection:
            self.scene().removeItem(self.temp_connection)
            self.temp_connection = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.main_window.connecting and self.connection_start:
            painter = QPainter(self.viewport())
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            start_pos = self.mapFromScene(self.connection_start.scenePos())
            end_pos = self.mapFromGlobal(self.cursor().pos())
            painter.drawLine(start_pos, end_pos)

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
        
        # Set the window to fill the screen

        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)
        
        # Adjust scene rect to match the screen size
        screen_rect = QApplication.desktop().screenGeometry()
        self.view.setSceneRect(0, 0, screen_rect.width(), screen_rect.height())
        self.view.setRenderHint(QPainter.Antialiasing)
        
        self.draw_grid()
        
        button_layout = QHBoxLayout()
        
        self.add_component_button = QPushButton("Add Component")
        self.add_component_button.clicked.connect(self.add_component)
        button_layout.addWidget(self.add_component_button)

        self.connecting = False
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
        
        self.rotating = False
        self.connection_source = None
        self.undo_stack = []
        self.redo_stack = []
        
    def add_component(self):
        dialog = ComponentDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
        
            if data["component_type"] == "IC Chip":
                if data["chip_type"] == "Regular":
                    width, height = 100, 50
                elif data["chip_type"] == "Wide":
                    width, height = 150, 50
                else:  # Square
                    width, height = 100, 100
            elif data["component_type"] == "Capacitor":
                width, height = 20, 40 
            elif data["component_type"] in ["Resistor", "Inductor"]:
                width, height = 60, 20
            elif data["component_type"] == "Crystal Oscillator":
                width, height = 40, 60
            elif data["component_type"] == "Diode":
                width, height = 40, 40
            elif data["component_type"] == "DIP Switch":
                width, height = max(20, data["pin_count"] * 10), 30
        
            component = FPGAComponent(0, 0, width, height, data["label"], data["pin_count"], data["pin_orientation"], data["component_type"])
            self.scene.addItem(component)
            self.undo_stack.append({"action": "add_component", "item": component})
            self.redo_stack = []

    def toggle_connection_mode(self):
        self.connecting = not self.connecting
        if self.connecting:
            self.add_connection_button.setText("Cancel Connection")
            self.view.setCursor(Qt.CrossCursor)
        else:
            self.add_connection_button.setText("Add Connection")
            self.view.setCursor(Qt.ArrowCursor)
            if self.view.connection_start:
                self.view.connection_start.setBrush(QBrush(Qt.black))
                self.view.connection_start = None
                
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
            line = self.scene.addLine(x, rect.top(), x, rect.bottom(), QPen(Qt.lightGray))
            line.setZValue(-2)  # Set grid lines below everything else
        for y in range(int(rect.top()), int(rect.bottom()), GRID_SIZE):
            line = self.scene.addLine(rect.left(), y, rect.right(), y, QPen(Qt.lightGray))
            line.setZValue(-2)  # Set grid lines below everything else

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
                component.setZValue(0) # Ensure components are above connections but below pins
                components[component_data["label"]] = component
            for connection_data in project_data["connections"]:
                source_component = components[connection_data["source_label"]]
                target_component = components[connection_data["target_label"]]
                source_pin = source_component.pins[connection_data["source_pin_index"]]
                target_pin = target_component.pins[connection_data["target_pin_index"]]
                connection = Connection(source_pin, target_pin)
                self.scene.addItem(connection)
                connection.setZValue(-1)  # Ensure connections are below components

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())