import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                            QSlider, QPushButton, QFileDialog, QHBoxLayout, 
                            QVBoxLayout, QStyle, QSizePolicy, QMessageBox)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QIcon, QFont, QImage, QPixmap
import cv2
import threading
import time

class HybridVideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能视频播放器")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.mainLayout = QVBoxLayout(self.centralWidget)
        
        # 视频显示组件
        self.videoWidget = QVideoWidget()
        self.videoWidget.setMinimumSize(800, 450)
        self.mainLayout.addWidget(self.videoWidget, 9)  # 90%高度
        
        # 创建备选图像标签（用于OpenCV模式）
        self.fallbackLabel = QLabel()
        self.fallbackLabel.setAlignment(Qt.AlignCenter)
        self.fallbackLabel.setStyleSheet("background-color: black;")
        self.fallbackLabel.setMinimumSize(800, 450)
        self.mainLayout.addWidget(self.fallbackLabel)
        self.fallbackLabel.hide()
        
        # 播放模式指示器
        self.modeLabel = QLabel("播放模式: Qt多媒体")
        self.modeLabel.setFont(QFont("Arial", 10, QFont.Bold))
        self.modeLabel.setStyleSheet("color: #FF5722;")
        self.mainLayout.addWidget(self.modeLabel)
        
        # 创建控制面板
        self.setup_controls()
        
        # 媒体播放器
        self.qtPlayer = QMediaPlayer()
        self.qtPlayer.setVideoOutput(self.videoWidget)
        
        # OpenCV视频状态
        self.cap = None
        self.using_cv = False
        self.cv_timer = QTimer()
        
        # 设置环境变量（Windows平台）
        if sys.platform == "win32":
            os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"

        # 新增：连接信号
        self.qtPlayer.positionChanged.connect(self.update_position)
        self.qtPlayer.durationChanged.connect(self.update_duration)
        self.positionSlider.sliderMoved.connect(self.set_position)
    
    def update_position(self, position):
        """更新Qt模式下的播放进度"""
        if self.qtPlayer.duration() > 0:
            # 更新进度条
            progress = (position / self.qtPlayer.duration()) * 1000
            self.positionSlider.setValue(int(progress))
            
            # 更新时间显示
            self.update_time_display(position, self.qtPlayer.duration())
    
    def update_duration(self, duration):
        """更新视频总时长"""
        if duration > 0:
            self.positionSlider.setRange(0, 1000)
            self.update_time_display(self.qtPlayer.position(), duration)
    
    def update_time_display(self, position, duration):
        """格式化显示时间"""
        total_seconds = duration // 1000
        current_seconds = position // 1000
        
        total_time = f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"
        current_time = f"{current_seconds // 60:02d}:{current_seconds % 60:02d}"
        
        self.timeLabel.setText(f"{current_time} / {total_time}")
    
    def set_position(self, position):
        """设置播放位置（通过拖动进度条）"""
        if self.using_cv:
            if self.cap:
                # 计算目标帧位置
                total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
                target_frame = int((position / 1000) * total_frames)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        else:
            if self.qtPlayer.duration() > 0:
                target_pos = int((position / 1000) * self.qtPlayer.duration())
                self.qtPlayer.setPosition(target_pos)
                
    def setup_controls(self):
        """创建播放控制面板"""
        # 控制按钮区域
        controlLayout = QHBoxLayout()
        
        # 播放按钮
        self.playBtn = QPushButton()
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.setFixedSize(50, 40)
        self.playBtn.clicked.connect(self.play_video)
        
        # 进度条
        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 100)
        self.positionSlider.setFixedHeight(30)
        
        # 时间显示
        self.timeLabel = QLabel("00:00 / 00:00")
        self.timeLabel.setFixedWidth(120)
        
        # 音量控件
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(80)
        self.volumeSlider.setFixedWidth(80)
        
        # 打开按钮
        self.openBtn = QPushButton("打开视频")
        self.openBtn.setFixedSize(100, 40)
        self.openBtn.clicked.connect(self.open_file)
        
        # 模式切换按钮
        self.modeBtn = QPushButton("切换播放引擎")
        self.modeBtn.setFixedSize(150, 40)
        self.modeBtn.clicked.connect(self.toggle_playback_mode)
        
        # 状态标签
        self.statusLabel = QLabel("准备就绪 - 请打开视频文件")
        self.statusLabel.setFont(QFont("Arial", 10))
        
        # 添加到布局
        controlLayout.addWidget(self.playBtn)
        controlLayout.addWidget(self.positionSlider, 6)  # 60%宽度
        controlLayout.addWidget(self.timeLabel)
        controlLayout.addWidget(QLabel("音量:"))
        controlLayout.addWidget(self.volumeSlider)
        controlLayout.addWidget(self.openBtn)
        controlLayout.addWidget(self.modeBtn)
        
        # 添加到主布局
        self.mainLayout.addLayout(controlLayout)
        self.mainLayout.addWidget(self.statusLabel)

        # 修改进度条范围
        self.positionSlider.setRange(0, 1000)  # 更精细的控制
    
    def open_file(self):
        """打开视频文件"""
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm *.mpg);;所有文件 (*.*)",
            options=options
        )
        
        if fileName:
            self.load_video(fileName)
    
    def load_video(self, file_path):
        """加载视频并自动选择最佳播放方式"""
        # 重置状态
        self.stop_playback()
        self.current_file = file_path
        self.statusLabel.setText(f"加载中: {os.path.basename(file_path)}")
        self.qtPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        
        # 尝试Qt播放
        QTimer.singleShot(1000, lambda: self.check_qt_playback())
    
    def check_qt_playback(self):
        """检查Qt播放是否成功"""
        if self.qtPlayer.mediaStatus() == QMediaPlayer.InvalidMedia:
            self.statusLabel.setText("Qt引擎不支持 - 尝试备选方案")
            # 尝试OpenCV备选播放
            self.start_opencv_playback(self.current_file)
        else:
            self.modeLabel.setText("播放模式: Qt多媒体")
            self.statusLabel.setText("Qt引擎已加载")
    
    def start_opencv_playback(self, file_path):
        """启动OpenCV播放模式"""
        try:
            # 释放之前的资源
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                raise Exception("无法通过OpenCV打开视频")
                
            # 获取视频信息
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_delay = max(10, int(1000 / fps)) if fps > 0 else 40
            self.total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            
            # 显示模式提示
            self.using_cv = True
            self.modeLabel.setText("播放模式: OpenCV硬件加速")
            
            # 显示OpenCV渲染区域
            self.videoWidget.hide()
            self.fallbackLabel.show()
            
            # 启动定时器
            self.cv_timer.timeout.connect(self.update_cv_frame)
            self.cv_timer.start(self.frame_delay)
            self.statusLabel.setText(f"OpenCV播放中: {self.get_video_codec_name()}")

            self.positionSlider.setValue(0)
            self.update_time_display(0, self.total_frames * 1000 / fps if fps > 0 else 0)
            
        except Exception as e:
            self.statusLabel.setText(f"OpenCV错误: {str(e)}")
            # 最后备选方案：调用系统播放器
            QTimer.singleShot(2000, lambda: self.launch_system_player(file_path))
    
    def get_video_codec_name(self):
        """获取视频编解码器名称"""
        if not self.cap:
            return "未知"
        
        # 在OpenCV中获取编码类型
        codec_id = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        codec_name = "".join([chr((codec_id >> 8 * i) & 0xFF) for i in range(4)])
        return f"{codec_name}编码"
    
    def update_cv_frame(self):
        """OpenCV模式更新帧"""
        if not self.cap:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.cv_timer.stop()
            self.statusLabel.setText("播放完成")
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            return
            
        # 转换并显示帧
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.fallbackLabel.setPixmap(pixmap.scaled(
            self.fallbackLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        
        # 更新进度
        if self.total_frames > 0:
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            progress = (current_frame / self.total_frames) * 1000
            self.positionSlider.setValue(int(progress))
            
            # 更新时间显示
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                current_time = current_frame / fps * 1000
                total_time = self.total_frames / fps * 1000
                self.update_time_display(current_time, total_time)
    
    def launch_system_player(self, file_path):
        """作为最后手段：调用系统默认播放器"""
        self.statusLabel.setText("正在调用系统播放器...")
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
            self.statusLabel.setText("已调用系统播放器")
        except:
            self.statusLabel.setText("无法调用系统播放器")
    
    def toggle_playback_mode(self):
        """手动切换播放模式"""
        if not hasattr(self, 'current_file'):
            return
            
        if self.using_cv:
            # 尝试切换回Qt模式
            self.switch_to_qt_mode()
        else:
            # 尝试切换到OpenCV模式
            self.stop_playback()
            self.start_opencv_playback(self.current_file)
    
    def switch_to_qt_mode(self):
        """切换回Qt播放模式"""
        self.using_cv = False
        self.cv_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
        # 恢复Qt播放控件
        self.fallbackLabel.hide()
        self.videoWidget.show()
        
        # 重试加载
        self.qtPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_file)))
        self.play_video()
        self.modeLabel.setText("播放模式: Qt多媒体")
        self.statusLabel.setText("已切换回Qt播放模式")
    
    def play_video(self):
        """播放/暂停控制"""
        if not hasattr(self, 'current_file'):
            return
            
        if self.using_cv:
            # OpenCV模式处理
            if self.cv_timer.isActive():
                self.cv_timer.stop()
                self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.statusLabel.setText("已暂停 (OpenCV)")
            else:
                self.cv_timer.start(self.frame_delay)
                self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.statusLabel.setText("播放中 (OpenCV)")
        else:
            # Qt模式处理
            if self.qtPlayer.state() == QMediaPlayer.PlayingState:
                self.qtPlayer.pause()
                self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.statusLabel.setText("已暂停 (Qt)")
            else:
                self.qtPlayer.play()
                self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.statusLabel.setText("播放中 (Qt)")
    
    def stop_playback(self):
        """停止当前播放"""
        if self.using_cv:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.cv_timer.stop()
        else:
            self.qtPlayer.stop()
        
        # 重置进度显示
        self.positionSlider.setValue(0)
        self.timeLabel.setText("00:00 / 00:00")
    
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.stop_playback()
        event.accept()

    # 新增：检测Windows系统是否已安装任何主流解码器的函数
def is_codec_installed():
    if sys.platform != "win32":
        return True  # 非Windows系统不需要检测
    
    # 检查注册表中的常见解码器条目
    try:
        import winreg
        try:
            # 检查K-Lite Codec Pack的注册表信息
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KLiteCodecPack") as key:
                return True  # 如果注册表键存在
        except FileNotFoundError:
            pass
        
        # 检查FFDshow等其他常见解码器
        known_codecs = ["ffdshow", "LAV Filters", "LAME"]
        for codec in known_codecs:
            try:
                winreg.EnumKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
                # 实际实现中需要遍历子键判断是否包含指定字符串
                return True
            except:
                continue
        
        # 作为备选方案，尝试播放一个测试视频
        try:
            from PyQt5.QtMultimedia import QMediaPlayer
            player = QMediaPlayer()
            player.setMedia(QMediaContent(QUrl.fromLocalFile(r"C:\Windows\Media\onestop.mid")))
            return player.mediaStatus() != QMediaPlayer.InvalidMedia
        except:
            return False
    except ImportError:
        # 非Windows系统直接返回True
        return True
    except:
        return True  # 出错时默认视为已安装
    
# 主程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 检查并安装必要的解码器包（Windows）
    if sys.platform == "win32" and not is_codec_installed():
        reply = QMessageBox.question(
            None, "安装解码器",
            "检测到系统缺少解码器包，是否立即下载安装?\n(推荐安装以保证最佳兼容性)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import webbrowser
            webbrowser.open("https://codecguide.com/download_kl.htm")
    
    player = HybridVideoPlayer()
    player.show()
    sys.exit(app.exec_())