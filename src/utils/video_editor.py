import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import random
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip

from .logger import VideoLogger

class VideoEditor:
    logger = VideoLogger()

    @staticmethod
    def get_random_video(input_dir):
        video_files = [f for f in os.listdir(input_dir) 
                      if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        if not video_files:
            VideoEditor.logger.error(f"在{input_dir}目录中没有找到视频文件")
            raise ValueError(f"在{input_dir}目录中没有找到视频文件")
        VideoEditor.logger.info(f"从{input_dir}中随机选择视频文件")
        return os.path.join(input_dir, random.choice(video_files))

    @staticmethod
    def get_random_audio(input_dir):
        audio_files = [f for f in os.listdir(input_dir) 
                      if f.lower().endswith(('.mp3', '.wav'))]
        if not audio_files:
            raise ValueError(f"在{input_dir}目录中没有找到音频文件")
        return os.path.join(input_dir, random.choice(audio_files))

    def __init__(self, video_path):
        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")
        
        valid_formats = ('.mp4', '.avi', '.mov')
        if not video_path.lower().endswith(valid_formats):
            raise ValueError(f"不支持的视频格式。支持的格式: {', '.join(valid_formats)}")
        
        try:
            self.video = VideoFileClip(video_path, audio=False)
            if self.video.duration is None:
                raise ValueError("无法获取视频时长，视频文件可能已损坏")
            # 设置固定的输出分辨率
            self.width = 1080
            self.height = 1920
            # 调整视频大小以适应目标分辨率
            self.video = self.video.resize((self.width, self.height))
            
            # 加载随机背景音乐
            audio_path = self.get_random_audio('asset/audio')
            self.audio = AudioFileClip(audio_path)
        except Exception as e:
            raise ValueError(f"无法加载视频或音频文件: {str(e)}")
        
        self.overlays = []

    def _calculate_position(self, position, text_width=0, text_height=0):
        x, y = position
        if isinstance(x, str) and x.endswith('%'):
            x = int(float(x[:-1]) * self.width / 100)
        if isinstance(y, str) and y.endswith('%'):
            y = int(float(y[:-1]) * self.height / 100)
        
        # 只限制y坐标不超出视频边界
        y = max(0, min(y, self.height - text_height))
        return (x, y)

    def create_text_image(self, text, font_size=30, color='white', stroke_color='black', stroke_width=2):
        """创建高清晰度的中文文本图片（支持旋转抗锯齿）"""
        # 高清渲染参数
        scale_factor = 3.0  # 提高分辨率渲染倍数
        font_size_scaled = int(font_size * scale_factor)
        stroke_width_scaled = max(1, int(stroke_width * (scale_factor * 0.25)))  # 进一步降低描边宽度的缩放比例

        # 中文字体加载（优先使用自定义字体文件）
        try:
            # 尝试加载多个平台的系统字体
            font_paths = [
                'assets/font/PingFang.ttc',  # 项目目录下的字体文件
                '/System/Library/Fonts/PingFang.ttc',  # Mac
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux
                'C:/Windows/Fonts/simhei.ttf',  # Windows
            ]
            
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size_scaled)
                    break
                except:
                    continue
            else:
                raise IOError("No valid font found")
        except Exception as e:
            raise RuntimeError(f"字体加载失败: {str(e)}，请确认已安装中文字体")

        # 计算文本尺寸（考虑描边和边距）
        temp_img = Image.new('RGBA', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width_scaled)
        
        # 边距计算（包含描边扩展区域）
        padding = int(font_size_scaled * 0.3)  # 基础边距
        text_width = bbox[2] - bbox[0] + padding * 2
        text_height = bbox[3] - bbox[1] + padding * 2

        # 创建高清画布
        img = Image.new('RGBA', 
            (text_width + stroke_width_scaled*4, 
            text_height + stroke_width_scaled*4),
            (0, 0, 0, 0)
        )
        draw = ImageDraw.Draw(img)

        # 文本绘制位置（居中+边距）
        x = stroke_width_scaled * 2 + padding
        y = stroke_width_scaled * 2 + padding

        # 使用Pillow内置描边功能（版本8.0+）
        draw.text(
            (x, y), text, 
            font=font, 
            fill=color,
            stroke_width=stroke_width_scaled,
            stroke_fill=stroke_color
        )

        # 下采样并锐化（保持边缘清晰）
        img = img.resize(
            (int(img.width // scale_factor), int(img.height // scale_factor)),
            resample=Image.LANCZOS
        )
        img = img.filter(ImageFilter.SHARPEN)

        # 返回PIL图像对象
        return img

    def add_text(self, text, position, font_size=30, color='white', start_time=0, end_time=None, typewriter_effect=False, typing_speed=0.1, center_on_last_image=False, rotation_angle=0, stroke_width=None):
        """添加中文文本到视频"""
        if end_time is None:
            end_time = self.video.duration

        # 根据文字位置决定是否使用描边效果和自动换行
        if stroke_width is None:
            use_stroke = position[1] == 967 if isinstance(position, tuple) else False
            stroke_width = 2 if use_stroke else 0

        # 处理左侧评论的自动换行（y坐标为410时）
        if isinstance(position, tuple) and position[1] == 410:
            chars_per_line = 16
            text_lines = [text[i:i + chars_per_line] for i in range(0, len(text), chars_per_line)]
            text = '\n'.join(text_lines)

        # 创建文字图片
        text_image = self.create_text_image(text, font_size, color, stroke_width=stroke_width)
        text_width, text_height = text_image.size
        
        # 计算位置
        if center_on_last_image and hasattr(self, 'last_image_size') and hasattr(self, 'last_image_position'):
            img_width, img_height = self.last_image_size
            img_x, img_y = self.last_image_position
            x = img_x + (img_width - text_width) // 2
            y = img_y + (img_height - text_height) // 2
            position = (x, y)
        
        actual_position = self._calculate_position(position, text_width, text_height)

        # 优化打字机效果的实现
        if typewriter_effect:
            # 预先创建所有字符的图片
            text_clips = []
            for i in range(len(text)):
                current_text = text[:i+1]
                text_image = self.create_text_image(current_text, font_size, color)
                text_clip = ImageClip(np.array(text_image), transparent=True)
                if rotation_angle != 0:
                    text_clip = text_clip.rotate(rotation_angle, resample='bilinear', expand=True)
                clip_start = start_time + i * typing_speed
                text_clip = text_clip.set_position(actual_position).set_start(clip_start).set_end(end_time)
                text_clips.append(text_clip)
            self.overlays.extend(text_clips)
        else:
            # 非打字机效果直接添加一个文字clip
            text_clip = ImageClip(np.array(text_image), transparent=True)
            if rotation_angle != 0:
                text_clip = text_clip.rotate(rotation_angle, resample='bilinear', expand=True)
            text_clip = text_clip.set_position(actual_position).set_start(start_time).set_end(end_time)
            self.overlays.append(text_clip)

    def add_image(self, image_path, position, size=None, start_time=0, end_time=None):
        if end_time is None:
            end_time = self.video.duration

        img_clip = ImageClip(image_path)
        actual_position = self._calculate_position(position)

        if size:
            w, h = size
            if isinstance(w, str) and w.endswith('%'):
                w = int(float(w[:-1]) * self.width / 100)
            if isinstance(h, str) and h.endswith('%'):
                h = int(float(h[:-1]) * self.height / 100)
            
            # 如果height为None，根据width保持原始宽高比
            if h is None:
                aspect_ratio = img_clip.size[1] / img_clip.size[0]
                h = int(w * aspect_ratio)
            
            img_clip = img_clip.resize((w, h))
        
        # 获取图片尺寸
        self.last_image_size = img_clip.size
        self.last_image_position = actual_position
        
        img_clip = img_clip.set_position(actual_position).set_start(start_time).set_end(end_time)
        self.overlays.append(img_clip)

    def render(self, output_path):
        """渲染并保存视频"""
        try:
            self.logger.info(f"开始渲染视频到: {output_path}")
            # 计算所需的总时长（基于所有叠加层的最大结束时间）
            max_duration = max(clip.end for clip in self.overlays) if self.overlays else self.video.duration
            self.logger.debug(f"计算的视频总时长: {max_duration}秒")
            
            # 如果原始视频时长小于所需时长，创建循环播放的视频
            if max_duration > self.video.duration:
                self.logger.info(f"需要循环播放视频: 原始时长{self.video.duration}秒, 目标时长{max_duration}秒")
                # 计算需要循环的次数（向上取整）
                loop_count = int(max_duration / self.video.duration) + 1
                # 创建循环视频
                looped_video = self.video.loop(n=loop_count)
                # 裁剪到所需时长
                looped_video = looped_video.subclip(0, max_duration)
                # 循环并裁剪音频以匹配视频时长
                looped_audio = self.audio.loop(duration=max_duration)
                looped_video = looped_video.set_audio(looped_audio)
                final_video = CompositeVideoClip([looped_video] + self.overlays)
            else:
                self.logger.info("使用原始视频时长")
                # 裁剪音频以匹配视频时长
                video_audio = self.audio.subclip(0, self.video.duration)
                video_with_audio = self.video.set_audio(video_audio)
                final_video = CompositeVideoClip([video_with_audio] + self.overlays)
            
            # 设置优化参数
            self.logger.info("开始写入视频文件，使用优化参数")
            final_video.write_videofile(
                output_path,
                codec='h264_nvenc' if self._has_cuda() else 'libx264',  # 优先使用NVIDIA GPU编码
                audio_codec='aac',
                preset='p1' if self._has_cuda() else 'veryfast',  # NVENC预设或CPU预设
                threads=12,      # 增加线程数以提升性能
                bitrate='2000k',  # 保持适中的比特率
                fps=30,         # 设置固定帧率
                write_logfile=False,  # 关闭日志文件写入
                temp_audiofile=False,  # 禁用临时音频文件
                remove_temp=True   # 及时删除临时文件
            )
            final_video.close()
            self.video.close()
            self.audio.close()
            self.logger.info("视频渲染完成")
        except Exception as e:
            self.logger.error(f"渲染视频时出错: {str(e)}")
            raise

    def _has_cuda(self):
        """检查是否支持CUDA"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
