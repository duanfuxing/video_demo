from flask import Flask, render_template, request, send_file, jsonify
from src.utils.video_editor import VideoEditor
from src.services.render_count import RenderCountService
import os
import time
import random
import glob

app = Flask(__name__, template_folder='src/templates')
render_count_service = RenderCountService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # 获取表单数据
    typewriter_text = request.form['typewriter_text']
    static_text1 = request.form['static_text1']
    static_text2 = request.form['static_text2']
    static_text3 = request.form['static_text3']
    template_id = request.form['template_id']

    # 从视频目录选择视频
    input_dir = 'asset/video'  # 修改为使用统一的视频目录
    video_path = VideoEditor.get_random_video(input_dir)

    # 创建VideoEditor实例
    editor = VideoEditor(video_path)

    # 计算视频时长（基于打字机文字长度和静态文字显示需求）
    typing_speed = 0.3  # 每个字符的打字速度（秒）
    typing_duration = len(typewriter_text) * typing_speed + 1  # 加1秒作为开始延迟

    # 获取视频总时长
    video_duration = editor.video.duration

    # 添加打字机效果文字（在顶部20%的位置）
    editor.add_text(typewriter_text, position=('10%', '20%'),
                   font_size=80, color='white',
                   typewriter_effect=True, typing_speed=typing_speed,
                   start_time=1,  # 延迟1秒开始显示打字机效果
                   end_time=video_duration)  # 修改为视频总时长

    # 添加三段静态文字，从视频开始就显示
    editor.add_text(static_text1, position=('10%', '40%'),
                   font_size=60, color='white',
                   start_time=0,  # 从视频开始就显示
                   end_time=video_duration)  # 修改为视频总时长

    editor.add_text(static_text2, position=('10%', '60%'),
                   font_size=60, color='white',
                   start_time=0,  # 从视频开始就显示
                   end_time=video_duration)  # 修改为视频总时长

    editor.add_text(static_text3, position=('10%', '80%'),
                   font_size=60, color='white',
                   start_time=0,  # 从视频开始就显示
                   end_time=video_duration)  # 修改为视频总时长

    # 渲染并保存视频
    timestamp = int(time.time())
    random_num = random.randint(1000, 9999)
    output_filename = f'video_{template_id}_{timestamp}_{random_num}.mp4'
    output_path = os.path.join('output', output_filename)
    os.makedirs('output', exist_ok=True)
    editor.render(output_path)
    
    # 更新合成次数
    current_count = render_count_service.increment_count()
    
    # 返回视频文件和合成次数
    response = {
        'render_count': current_count,
        'video_url': f'/download/{output_filename}'
    }
    return jsonify(response)

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
    app.run(debug=True)