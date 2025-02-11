import schedule
import time
from clean_videos import clean_old_videos


def cleanup_job():
    """定时清理任务"""
    clean_old_videos(days=3)  # 清理3天前的视频


# 每天凌晨2点执行清理
schedule.every().day.at("02:00").do(cleanup_job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)
