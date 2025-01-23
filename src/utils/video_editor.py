import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import random
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip

class VideoEditor:
    @staticmethod
    def get_random_video(input_dir):
        video_files = [f for f in os.listdir(input_dir) 
                      if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        if not video_files:
            raise ValueError(f"在{input_dir}目录中没有找到视频文件")
        return os.path.join(input_dir, random.choice(video_files))

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
            self.width = int(self.video.w)
            self.height = int(self.video.h)
        except Exception as e:
            raise ValueError(f"无法加载视频文件: {str(e)}")
        
        self.overlays = []

    def _calculate_position(self, position, text_width=0, text_height=0):
        x, y = position
        if isinstance(x, str) and x.endswith('%'):
            x = int(float(x[:-1]) * self.width / 100)
        if isinstance(y, str) and y.endswith('%'):
            y = int(float(y[:-1]) * self.height / 100)
        
        # 确保文字不会超出视频边界
        x = max(0, min(x, self.width - text_width))
        y = max(0, min(y, self.height - text_height))
        return (x, y)

    def create_text_image(self, text, font_size=30, color='white', stroke_color='black', stroke_width=2):
        """创建包含中文文本的图片"""
        # 创建一个透明背景的图片
        # 先用小尺寸创建，之后会根据实际文字大小调整
        temp_img = Image.new('RGBA', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # 加载中文字体
        try:
            # 尝试使用系统中文字体
            font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', font_size)  # Mac系统
        except:
            try:
                font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', font_size)  # Linux系统
            except:
                # 如果都找不到，使用默认字体
                font = ImageFont.load_default()
                print("警告：未找到中文字体，使用默认字体")

        # 获取文本尺寸，增加额外的边距
        padding = font_size // 3  # 增加边距为字体大小的1/3
        bottom_padding = font_size // 2  # 底部额外增加字体大小的1/2作为边距
        bbox = temp_draw.textbbox((padding, padding), text, font=font)
        text_width = bbox[2] - bbox[0] + padding * 2
        text_height = bbox[3] - bbox[1] + padding * 2 + bottom_padding  # 增加底部边距

        # 创建适当大小的图片，考虑描边宽度和边距
        total_width = text_width + stroke_width * 4
        total_height = text_height + stroke_width * 4
        img = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 计算文字的实际绘制位置
        text_x = stroke_width * 2 + padding
        text_y = stroke_width * 2 + padding

        # 绘制描边
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                draw.text((text_x + offset_x, text_y + offset_y), text, font=font, fill=stroke_color)

        # 绘制主文本
        draw.text((text_x, text_y), text, font=font, fill=color)

        return img

    def add_text(self, text, position, font_size=30, color='white', start_time=0, end_time=None, typewriter_effect=False, typing_speed=0.1):
        """添加中文文本到视频"""
        if end_time is None:
            end_time = self.video.duration

        # 先创建文字图片以获取尺寸
        text_image = self.create_text_image(text, font_size, color)
        text_width, text_height = text_image.size
        
        # 计算位置时考虑文字尺寸
        actual_position = self._calculate_position(position, text_width, text_height)

        if not typewriter_effect:
            # 将图片转换为 MoviePy 的 ImageClip
            text_clip = ImageClip(np.array(text_image), transparent=True)
            text_clip = text_clip.set_position(actual_position).set_start(start_time).set_end(end_time)
            self.overlays.append(text_clip)
        else:
            # 打字机效果
            for i in range(len(text)):
                current_text = text[:i+1]
                text_image = self.create_text_image(current_text, font_size, color)
                current_width, current_height = text_image.size
                current_position = self._calculate_position(position, current_width, current_height)
                text_clip = ImageClip(np.array(text_image), transparent=True)
                clip_start = start_time + i * typing_speed
                # 修改这里，让每个字符在打字机效果结束后继续显示到视频结束
                clip_end = end_time
                text_clip = text_clip.set_position(current_position).set_start(clip_start).set_end(clip_end)
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
            img_clip = img_clip.resize((w, h))
        
        img_clip = img_clip.set_position(actual_position).set_start(start_time).set_end(end_time)
        self.overlays.append(img_clip)

    def render(self, output_path):
        """渲染并保存视频"""
        try:
            # 计算所需的总时长（基于所有叠加层的最大结束时间）
            max_duration = max(clip.end for clip in self.overlays) if self.overlays else self.video.duration
            
            # 如果原始视频时长小于所需时长，创建循环播放的视频
            if max_duration > self.video.duration:
                # 计算需要循环的次数（向上取整）
                loop_count = int(max_duration / self.video.duration) + 1
                # 创建循环视频
                looped_video = self.video.loop(n=loop_count)
                # 裁剪到所需时长
                looped_video = looped_video.subclip(0, max_duration)
                final_video = CompositeVideoClip([looped_video] + self.overlays)
            else:
                final_video = CompositeVideoClip([self.video] + self.overlays)
            
            final_video.write_videofile(output_path)
            final_video.close()
            self.video.close()
        except Exception as e:
            print(f"渲染视频时出错: {str(e)}")
            raise