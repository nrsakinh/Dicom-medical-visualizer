import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainterPath, QRegion
from PyQt5.QtCore import QRectF


class VideoSplashScreen(QWidget):
    def __init__(self, video_path, callback):
        super().__init__()
        self.callback = callback
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        self.setFixedSize(960, 540)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Layout with no margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget - fill entire space
        self.video_widget = QVideoWidget()
        self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)
        layout.addWidget(self.video_widget)
        
        # Apply rounded corners mask
        self.setRoundedMask()
        
        # Setup opacity effect for fade out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Media player
        self.media_player = QMediaPlayer(self)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Check if file exists
        if os.path.exists(video_path):
            print(f"Video file found: {video_path}")
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        else:
            print(f"ERROR: Video file not found: {video_path}")
        
        # Connect signals
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.error.connect(self.on_error)
    
    def setRoundedMask(self):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setRoundedMask()
    
    def on_error(self, error):
        print(f"Media player error: {error}")
        print(f"Error string: {self.media_player.errorString()}")
        # If error, still proceed to main app
        self.fade_out()
        
    def on_media_status_changed(self, status):
        print(f"Media status: {status}")
        if status == QMediaPlayer.EndOfMedia:
            self.fade_out()
        elif status == QMediaPlayer.InvalidMedia:
            print("Invalid media - codec may not be supported")
            self.fade_out()
    
    def fade_out(self):
        """Fade out animation before closing."""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.finished.connect(self.close_splash)
        self.animation.start()
    
    def close_splash(self):
        self.media_player.stop()
        self.close()
        self.callback()
    
    def start(self):
        self.show()
        self.media_player.play()
        print(f"Player state: {self.media_player.state()}")


def show_splash(video_path, callback):
    splash = VideoSplashScreen(video_path, callback)
    splash.start()
    return splash


def main():
    app = QApplication(sys.argv)
    
    # Import MainWindow from sakinah.py
    from main import MainWindow
    
    main_window = None
    
    def show_main():
        global main_window
        # Create MainWindow with auto_show=True
        main_window = MainWindow(auto_show=True)
    
    # Path to your splash video - update this path as needed
    video_path = r"D:\SDV2025\project_env1\SDV_Assignment 2_Nur Sakinah_BS22110305\Dataset\splash_screen.mp4"
    
    # Show splash screen, then open main application
    splash = show_splash(video_path, show_main)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()