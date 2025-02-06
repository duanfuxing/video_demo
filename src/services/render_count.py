import os
import fcntl

class RenderCountService:
    def __init__(self):
        self.count_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'render_count.txt')
        self._ensure_count_file()
    
    def _ensure_count_file(self):
        """确保计数文件存在"""
        os.makedirs(os.path.dirname(self.count_file), exist_ok=True)
        if not os.path.exists(self.count_file):
            with open(self.count_file, 'w') as f:
                f.write('0')
    
    def get_count(self):
        """获取当前计数"""
        with open(self.count_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return int(f.read().strip())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def increment_count(self):
        """增加计数并返回新值"""
        with open(self.count_file, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                current_count = int(f.read().strip())
                new_count = current_count + 1
                f.seek(0)
                f.truncate()
                f.write(str(new_count))
                return new_count
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)