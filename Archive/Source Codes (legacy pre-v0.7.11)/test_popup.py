import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QScrollArea, QLabel, QVBoxLayout, QWidget, QFrame

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.btn = QPushButton("Open Popup", self)
        self.btn.clicked.connect(self.open_popup)
        self.setCentralWidget(self.btn)
        
        self.popup = QScrollArea()
        self.popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setWidgetResizable(True)
        self.popup.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        for i in range(20):
            layout.addWidget(QLabel(f"Item {i}"))
        self.popup.setWidget(content)
        
    def open_popup(self):
        self.popup.resize(200, 200)
        self.popup.move(self.btn.mapToGlobal(self.btn.rect().bottomLeft()))
        self.popup.show()

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
