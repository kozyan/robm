import os
import threading
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import streamlit as st
import logging

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 应用
flask_app = Flask(__name__)

# 环境变量
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
JENKINS_URL = os.getenv('JENKINS_URL')  # 例如: http://your-jenkins-server:8080
JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')
JENKINS_JOB = os.getenv('JENKINS_JOB')  # 例如: my-job
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # 例如: https://your-app.streamlit.app/webhook

# 初始化 Telegram 机器人
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Streamlit 页面
def run_streamlit():
    st.set_page_config(page_title="Jenkins Bot Dashboard", layout="wide")
    st.title("Jenkins Telegram Bot Dashboard")
    st.write("This bot is running and connected to Jenkins.")
    st.write(f"Webhook URL: {WEBHOOK_URL}")
    st.write(f"Jenkins Job: {JENKINS_JOB}")
    
    if st.button("Manually Trigger Build"):
        try:
            build_url = f"{JENKINS_URL}/job/{JENKINS_JOB}/build"
            auth = (JENKINS_USER, JENKINS_TOKEN)
            response = requests.post(build_url, auth=auth)
            if response.status_code == 201:
                st.success("Build triggered successfully!")
            else:
                st.error(f"Failed to trigger build: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    await update.message.reply_text(
        "欢迎使用 Jenkins 编译机器人！\n"
        "可用命令：\n"
        "/build - 触发 Jenkins 构建\n"
        "/status - 获取最新构建状态"
    )

async def build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """触发 Jenkins 构建"""
    try:
        build_url = f"{JENKINS_URL}/job/{JENKINS_JOB}/build"
        auth = (JENKINS_USER, JENKINS_TOKEN)
        response = requests.post(build_url, auth=auth)
        if response.status_code == 201:
            await update.message.reply_text("构建已触发！请稍后使用 /status 检查状态。")
        else:
            await update.message.reply_text(f"触发构建失败：{response.status_code} - {response.text}")
    except Exception as e:
        await update.message.reply_text(f"错误：{str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """获取最新构建状态"""
    try:
        status_url = f"{JENKINS_URL}/job/{JENKINS_JOB}/lastBuild/api/json"
        auth = (JENKINS_USER, JENKINS_TOKEN)
        response = requests.get(status_url, auth=auth)
        response.raise_for_status()
        data = response.json()
        build_number = data.get('number', '未知')
        result = data.get('result', '未知')
        timestamp = data.get('timestamp', '未知')
        message = (
            f"最新构建 #{build_number}\n"
            f"状态: {result}\n"
            f"时间: {timestamp}"
        )
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"获取状态失败：{str(e)}")

# Flask 路由处理 Webhook
@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'OK'

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8501)))

if __name__ == '__main__':
    # 添加 Telegram 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("build", build))
    application.add_handler(CommandHandler("status", status))
    
    # 设置 Webhook
    application.bot.set_webhook(url=WEBHOOK_URL)
    
    # 在单独线程中运行 Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # 运行 Streamlit
    run_streamlit()