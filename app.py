from flask import Flask, render_template, request, send_file, jsonify
from src.utils.video_editor import VideoEditor
from src.services.render_count import RenderCountService
import os
import time
import random
import glob
import gc  # 添加 gc 模块导入

app = Flask(__name__, template_folder='src/templates')
render_count_service = RenderCountService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        # 获取表单数据
        bottom_comment = request.form['bottom_comment']
        shop_name = request.form['shop_name']
        left_comment = request.form['left_comment']
        right_comment = request.form['right_comment']
        template_id = request.form['template_id']
        
        # 验证输入文字长度
        if len(shop_name) > 15:
            return jsonify({'error': '店名不能超过15个字符'}), 400
        if len(left_comment) > 120:
            return jsonify({'error': '左侧评论不能超过120个字符'}), 400
        if len(right_comment) > 12:
            return jsonify({'error': '右侧评论不能超过12个字符'}), 400
        if len(bottom_comment) > 100:
            return jsonify({'error': '底部评论不能超过100个字符'}), 400
    
        # 从视频目录选择视频
        input_dir = 'asset/video'  # 修改为使用统一的视频目录
        video_path = VideoEditor.get_random_video(input_dir)
    
        # 创建VideoEditor实例
        editor = VideoEditor(video_path)
    
        # 计算视频时长（基于打字机文字长度和静态文字显示需求）
        typing_speed = 0.3  # 每个字符的打字速度（秒）
        typing_duration = len(bottom_comment) * typing_speed + 3  # 加1秒作为开始延迟
    
        # 获取视频总时长，如果打字机效果需要的时间更长，则通过循环来延长视频时长
        original_duration = editor.video.duration
        video_duration = max(original_duration, typing_duration)
        if video_duration > original_duration:
            editor.video = editor.video.loop(duration=video_duration)
    
        # 先创建文字对象以获取尺寸
        text_image = editor.create_text_image(shop_name, font_size=48, color='black')
        text_width, text_height = text_image.size
        
        # 添加title.png图片，根据文字宽度调整大小
        # 设置最小宽度为原始宽度的一半，确保短文本时图片也有合适的大小
        min_width = 402  # 原始宽度
        img_width = max(min_width, text_width + 100)  # 文字宽度加上左右边距
        
        # 添加title.png图片
        editor.add_image('asset/images/title.png', 
                       position=((1080 - img_width) // 2, 148),  # 水平居中
                       size=(img_width, None),  # 只设置宽度，保持原始比例
                       start_time=0,
                       end_time=video_duration)
    
        # 添加店名文字（垂直居中）
        title_height = 80  # title.png的高度
        text_y = 148 + (title_height - text_height) // 2  # 计算垂直居中位置
        editor.add_text(shop_name, position=((1080 - text_width) // 2, text_y),
                       font_size=48, color='black',
                       start_time=0,
                       end_time=video_duration)
    
        # 添加底部评论背景图片
        editor.add_image('asset/images/bottom_evaluate.png',
                       position=(-120, 967),
                       size=(1300, 447),
                       start_time=0,
                       end_time=video_duration)
    
        # 添加底部评论文字
        editor.add_text(bottom_comment, position=(60, 1080),
                       font_size=30, color='black',
                       typewriter_effect=True, typing_speed=typing_speed,
                       start_time=0.1,  # 延迟1秒开始显示打字机效果
                       end_time=video_duration)  # 修改为视频总时长
        # 添加底部好外卖名称
        editor.add_text("——好外卖分部", position=(590, 1240),
                       font_size=62, color='red',
                       start_time=0,  # 从视频开始就显示
                       end_time=video_duration)  # 修改为视频总时长
    
        # 添加左侧评论背景图片
        editor.add_image('asset/images/five_star.png',
                       position=(14, 342),
                       start_time=0,
                       end_time=video_duration)
    
        # 添加左侧评论文字
        editor.add_text(left_comment, position=(55, 410),
                       font_size=30, color='black',
                       start_time=0,  # 从视频开始就显示
                       end_time=video_duration)  # 修改为视频总时长
    
        # 添加右侧评论背景图片
        editor.add_image('asset/images/right_evaluate.png',
                       position=(548, 332),
                       start_time=0,
                       end_time=video_duration)
    
        # 添加右侧评论文字
        editor.add_text(right_comment, position=(630, 660),
                       font_size=36, color='black',
                       start_time=0,  # 从视频开始就显示
                       end_time=video_duration,
                       rotation_angle=5,  # 添加5度向上倾斜
                       stroke_width=3)  # 增加描边宽度以提升清晰度
    
        # 添加右侧字数统计
        right_cnt_str = "足足 " + str(len(left_comment)) + " 个字"
        editor.add_text(right_cnt_str, position=(633, 505),
                       font_size=55, color='white',
                       start_time=0,  # 从视频开始就显示
                       end_time=video_duration,
                       rotation_angle=5,  # 添加5度向上倾斜
                       stroke_width=8)  # 增加描边宽度以提升清晰度
    
        # 添加底部logo图片
        editor.add_image('asset/images/bottom_logo.png',
                       position=(780, 1625),
                       size=(200, 200),
                       start_time=0,
                       end_time=video_duration)
        
        # 添加左下logo图片
        editor.add_image('asset/images/sale_logo.png',
                       position=(0, 1300),
                       size=(300, 324),
                       start_time=0,
                       end_time=video_duration)
    
        # 获取并更新合成次数
        new_count = render_count_service.increment_count()
        
        # 渲染并保存视频
        timestamp = int(time.time())
        random_num = random.randint(1000, 9999)
        output_filename = f'video_{template_id}_{timestamp}_{random_num}.mp4'
        output_path = os.path.join('output', output_filename)
        os.makedirs('output', exist_ok=True)
        
        editor.render(output_path)
        
        # 返回视频文件和合成次数
        response = {
            'render_count': new_count,
            'video_url': f'/download/{output_filename}'
        }
        return jsonify(response)
        
    except Exception as e:
        # 出错时也要清理资源
        if 'editor' in locals():
            editor.cleanup()
        gc.collect()
        return jsonify({'error': str(e)}), 400

@app.route('/get_count')
def get_count():
    count = render_count_service.get_count()
    return jsonify({'count': count})

@app.route('/templates')
def get_templates():
    input_dir = 'asset/video'
    video_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.avi', '.mov'))]
    video_files.sort()  # 按照文件名正序排列
    templates = [{
        'id': os.path.splitext(f)[0],  # 使用文件名（不含扩展名）作为ID
        'name': f'视频模板{os.path.splitext(f)[0]}'  # 使用文件名（不含扩展名）作为显示名称
    } for f in video_files]
    return jsonify(templates)

@app.route('/download/<filename>')
def download_video(filename):
    video_path = os.path.join('output', filename)
    if not os.path.exists(video_path):
        return jsonify({'error': '未找到对应的视频文件'}), 404
    return send_file(video_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)