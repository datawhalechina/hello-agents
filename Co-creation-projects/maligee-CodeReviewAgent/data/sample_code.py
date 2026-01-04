"""
示例代码：一个简单的用户管理系统
用于演示代码审查功能
"""

class UserManager:
    """用户管理类"""
    
    def __init__(self):
        self.users = []
    
    def add_user(self, name, age, email):
        """添加用户"""
        user = {"name": name, "age": age, "email": email}
        self.users.append(user)
        return True
    
    def get_user(self, name):
        """获取用户信息"""
        for user in self.users:
            if user["name"] == name:
                return user
        return None
    
    def delete_user(self, name):
        """删除用户"""
        for i, user in enumerate(self.users):
            if user["name"] == name:
                del self.users[i]
                return True
        return False

def calculate_average_age(users):
    """计算平均年龄"""
    total = 0
    for user in users:
        total += user["age"]
    return total / len(users)

def send_email(email, message):
    """发送邮件（模拟）"""
    print(f"发送邮件到 {email}: {message}")
    return True

