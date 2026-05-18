import os
import re
import time
import subprocess
import logging
import requests
import telebot
from telebot import types

# Configuration
BASE_PATH = "/root/agent-factory"
BOTS_PATH = f"{BASE_PATH}/docker-workspaces/bots"
TEMPLATES_PATH = f"{BASE_PATH}/templates"
GEMINI_API_KEY = "AIzaSyCg2ivlZRS9juY2fDaN2qwbSzQUlptKAhM"
MASTER_TOKEN = "8767877172:AAG1tzxhrczsJhLDCk7lI1cGLfZtGHO8c5g"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{BASE_PATH}/master_bot.log"),
        logging.StreamHandler()
    ]
)

def get_gemini_response(prompt, system_instruction):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"System: {system_instruction}\\nUser: {prompt}"}]}]}
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return None

def validate_code(code):
    required = ["import telebot", "bot.polling"]
    for req in required:
        if req not in code:
            return False, f"Missing required component: {req}"
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    return True, "Valid"

def deploy_bot(bot_name, token, code):
    is_valid, msg = validate_code(code)
    if not is_valid:
        return False, f"Code Validation Failed: {msg}"

    bot_dir = os.path.join(BOTS_PATH, bot_name)
    os.makedirs(bot_dir, exist_ok=True)
    
    with open(os.path.join(bot_dir, "main.py"), "w") as f: f.write(code)
    with open(os.path.join(bot_dir, ".env"), "w") as f: f.write(f"BOT_TOKEN={token}")
    with open(os.path.join(bot_dir, "requirements.txt"), "w") as f: f.write("pyTelegramBotAPI\\npython-dotenv\\nrequests\\n")
    
    dockerfile_content = """FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
"""
    with open(os.path.join(bot_dir, "Dockerfile"), "w") as f: f.write(dockerfile_content)
    
    container_name = f"bot_{bot_name}"
    try:
        subprocess.run(["docker", "build", "-t", container_name, bot_dir], check=True)
        subprocess.run(["docker", "rm", "-f", container_name], stderr=subprocess.DEVNULL)
        subprocess.run([
            "docker", "run", "-d", 
            "--name", container_name, 
            "--restart", "unless-stopped", 
            "--memory", "128m", 
            "--cpus", "0.5",
            "--env-file", os.path.join(bot_dir, ".env"), 
            container_name
        ], check=True)
        return True, container_name
    except Exception as e:
        return False, str(e)

bot = telebot.TeleBot(MASTER_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    help_text = """
🚀 *AI Bot Factory Platform*
/generate <TOKEN> <Description> - توليد بوت جديد
/bots - عرض جميع البوتات المشغلة
/stats - إحصائيات استهلاك الموارد
/logs <bot_name> - عرض سجلات بوت معين
/restart <bot_name> - إعادة تشغيل بوت
/stop <bot_name> - إيقاف بوت
/delete <bot_name> - حذف بوت نهائياً
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['generate'])
def handle_generate(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: /generate <TOKEN> <Description>")
        return
    
    token, description = parts[1], parts[2]
    bot_name = f"bot_{int(time.time())}"
    msg = bot.reply_to(message, "🤖 Analyzing request and selecting template...")
    
    template_files = os.listdir(TEMPLATES_PATH)
    template_prompt = f"Based on this description: '{description}', which template is best? Options: {template_files}. Return ONLY the filename."
    template_name = get_gemini_response(template_prompt, "You are a template selector. Return only the filename.")
    
    if not template_name or template_name not in template_files:
        template_name = "ai_assistant.py"
        
    with open(os.path.join(TEMPLATES_PATH, template_name), 'r') as f:
        template_code = f.read()
        
    bot.edit_message_text(f"📝 Using template: {template_name}. Modifying code...", chat_id=msg.chat.id, message_id=msg.message_id)
    
    modify_prompt = f"Modify this template code to match the description: '{description}'. Template:\\n{template_code}"
    modified_code_raw = get_gemini_response(modify_prompt, "You are a Python expert. Return ONLY the modified code in ```python block.")
    
    code_match = re.search(r'```python\\n(.*?)\\n```', modified_code_raw, re.DOTALL)
    code = code_match.group(1) if code_match else modified_code_raw
    
    success, result = deploy_bot(bot_name, token, code)
    if success:
        bot.edit_message_text(f"✅ Deployed: {result}\\nTemplate: {template_name}", chat_id=msg.chat.id, message_id=msg.message_id)
    else:
        bot.edit_message_text(f"❌ Failed: {result}", chat_id=msg.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['bots'])
def list_bots(message):
    try:
        output = subprocess.check_output(["docker", "ps", "--format", "{{.Names}} ({{.Status}})"], text=True)
        bots = [line for line in output.split('\\n') if line.startswith('bot_')]
        if not bots:
            bot.reply_to(message, "📭 No active bots found.")
        else:
            bot.reply_to(message, "🤖 *Active Bots:*\\n" + "\\n".join(bots), parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    try:
        output = subprocess.check_output(["docker", "stats", "--no-stream", "--format", "{{.Name}}: CPU {{.CPUPerc}}, RAM {{.MemUsage}}"], text=True)
        stats = [line for line in output.split('\\n') if line.startswith('bot_')]
        if not stats:
            bot.reply_to(message, "📊 No bot stats available.")
        else:
            bot.reply_to(message, "📊 *Resource Usage:*\\n" + "\\n".join(stats), parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['logs'])
def get_logs(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: /logs <bot_name>")
        return
    name = parts[1]
    try:
        logs = subprocess.check_output(["docker", "logs", "--tail", "20", name], text=True, stderr=subprocess.STDOUT)
        bot.reply_to(message, f"📋 *Logs for {name}:*\\n```\\n{logs}\\n```", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['restart', 'stop', 'delete'])
def manage_bot(message):
    cmd = message.text.split()[0][1:]
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, f"❌ Usage: /{cmd} <bot_name>")
        return
    name = parts[1]
    try:
        if cmd == 'restart':
            subprocess.run(["docker", "restart", name], check=True)
            bot.reply_to(message, f"🔄 Bot {name} restarted.")
        elif cmd == 'stop':
            subprocess.run(["docker", "stop", name], check=True)
            bot.reply_to(message, f"🛑 Bot {name} stopped.")
        elif cmd == 'delete':
            subprocess.run(["docker", "rm", "-f", name], check=True)
            bot.reply_to(message, f"🗑️ Bot {name} deleted.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

if __name__ == "__main__":
    logging.info("🚀 Starting Monitoring Master Bot...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Polling Error: {e}")
            time.sleep(5)
