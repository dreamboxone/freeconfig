import urllib.request
import base64
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

# منابعی که توسط بات‌های داخل ایران تست و گلچین شده‌اند
SOURCES = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity"
]

def decode_base64(data):
    data = data.strip()
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    try: return base64.b64decode(data).decode('utf-8')
    except: return ""

def get_configs():
    configs = set()
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                text = response.read().decode('utf-8')
                if "://" not in text[:100]: text = decode_base64(text)
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith(("vmess://", "vless://", "trojan://", "ss://", "hysteria2://", "tuic://")):
                        configs.add(line)
        except Exception as e: print(f"Error fetching {url}: {e}")
    return list(configs)

def extract_host_port(config):
    try:
        if config.startswith("vmess://"):
            data = decode_base64(config[8:])
            info = json.loads(data)
            return info.get("add"), int(info.get("port"))
        else:
            match = re.search(r'@([^:]+):(\d+)', config)
            if match: return match.group(1), int(match.group(2))
    except: pass
    return None, None

def check_alive(config, timeout=2.0):
    host, port = extract_host_port(config)
    if not host or not port: return config, float('inf')
    
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return config, time.time() - start
    except: return config, float('inf')

def main():
    print("Fetching pre-tested configs for Iran...")
    configs = get_configs()
    print(f"Found {len(configs)} raw configs.")

    print("Running rapid socket health check...")
    tested_configs = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_alive, configs)
        for config, ping_time in results:
            if ping_time != float('inf'):
                tested_configs.append((config, ping_time))

    # مرتب‌سازی بر اساس کمترین پینگ سوکت
    tested_configs.sort(key=lambda x: x[1])
    
    # گلچین 30 کانفیگ برتر
    top_30 = [c[0] for c in tested_configs[:30]]
    
    print(f"Saving top {len(top_30)} configs.")
    plain_text = "\n".join(top_30)
    
    with open("sub.txt", "w", encoding="utf-8") as f: f.write(plain_text)
    
    base64_text = base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')
    with open("sub_base64.txt", "w", encoding="utf-8") as f: f.write(base64_text)
    print("Update Complete!")

if __name__ == "__main__": main()
