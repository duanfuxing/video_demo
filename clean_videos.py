import os
import time
import re
import argparse

def clean_old_videos(days=3):
    """清理指定天数之前的视频文件
    
    Args:
        days: 清理指定天数之前的文件，如果为0则清理所有文件
    Returns:
        int: 已删除的文件数量
    """
    # 获取脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    if not os.path.exists(output_dir):
        print(f"目录 {output_dir} 不存在")
        return

    # 获取当前时间戳
    current_time = int(time.time())
    # 计算截止时间戳（3天前）
    cutoff_time = current_time - (days * 24 * 60 * 60)

    # 正则表达式用于从文件名中提取时间戳
    timestamp_pattern = re.compile(r'video_\d+_(\d+)_\d+\.mp4')

    deleted_count = 0
    # 遍历输出目录中的所有文件
    for filename in os.listdir(output_dir):
        if not filename.endswith('.mp4'):
            continue

        should_delete = False
        if days == 0:  # 如果days为0，删除所有文件
            should_delete = True
        else:
            # 尝试从文件名中提取时间戳
            match = timestamp_pattern.match(filename)
            if match:
                file_timestamp = int(match.group(1))
                # 如果文件时间戳早于截止时间，删除文件
                if file_timestamp < cutoff_time:
                    should_delete = True

        if should_delete:
            file_path = os.path.join(output_dir, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f"已删除视频文件: {filename}")
            except Exception as e:
                print(f"删除文件 {filename} 时出错: {str(e)}")

    return deleted_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理指定天数之前的视频文件')
    parser.add_argument('--days', type=int, default=3,
                        help='清理指定天数之前的文件，设置为0则清理所有文件（默认：3天）')
    args = parser.parse_args()

    deleted_count = clean_old_videos(args.days)
    print(f"清理完成，共删除 {deleted_count} 个文件")