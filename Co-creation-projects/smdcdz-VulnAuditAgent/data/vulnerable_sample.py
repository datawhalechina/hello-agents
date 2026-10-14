"""示例：存在多处安全漏洞的 Flask 应用（仅用于教学演示，请勿用于生产）"""
import os
import pickle
import random
import sqlite3
import subprocess
import hashlib
import yaml
import requests
from flask import Flask, request

app = Flask(__name__)

# 硬编码密钥
API_KEY = "sk-live-abcdef1234567890"
DB_PASSWORD = "root123456"

def get_user():
    # SQL 注入：字符串拼接构造查询
    uid = request.args.get("uid")
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = " + uid)
    return cur.fetchall()

@app.route("/ping")
def ping():
    # 命令注入：用户输入直接进入 shell
    host = request.args.get("host")
    os.system("ping -c 1 " + host)
    return "ok"

@app.route("/calc")
def calc():
    # eval 执行用户输入
    expr = request.args.get("expr")
    return str(eval(expr))

@app.route("/load", methods=["POST"])
def load():
    # 不安全反序列化
    data = request.data
    return pickle.loads(data)

@app.route("/run")
def run_cmd():
    # subprocess shell=True
    cmd = request.args.get("cmd")
    subprocess.call(cmd, shell=True)
    return "done"

@app.route("/config")
def config():
    # yaml.load 未指定 SafeLoader
    text = request.args.get("yml")
    return yaml.load(text)

def make_token():
    # 弱随机数用于安全令牌
    return str(random.randint(100000, 999999))

def check_pwd(pw):
    # MD5 弱哈希存储密码
    return hashlib.md5(pw.encode()).hexdigest()

def fetch(url):
    # 关闭 TLS 证书验证
    return requests.get(url, verify=False).text