import urllib.request
import base64
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

# منابع معتبر برای جمع‌آوری کانفیگ‌های اولیه
SOURCES = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity"
]

def decode_base64(data):
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    try:
        return base64.b64decode(data).decode('utf-8')
    except:
        return ""

def get_configs():
    configs = set()
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                text = response.read().decode('utf-8')
                if "://" not in text[:100]:
                    text = decode_base64(text)
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith(("vmess://", "vless://", "trojan://", "ss://", "hysteria2://", "tuic://", "wireguard://")):
                        configs.add(line)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return list(configs)

def extract_host_port(config):
    try:
        if config.startswith("vmess://"):
            data = decode_base64(config[8:])
            info = json.loads(data)
            return info.get("add"), int(info.get("port"))
        else:
            match = re.search(r'@([^:]+):(\d+)', config)
            if match:
                return match.group(1), int(match.group(2))
    except:
        pass
    return None, None

def tcp_ping(host, port, timeout=2.0):
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return time.time() - start
    except:
        return float('inf')

def test_config(config):
    host, port = extract_host_port(config)
    if not host or not port:
        return config, float('inf')
    
    ping_time = tcp_ping(host, port)
    return config, ping_time

def main():
    print("Fetching configs...")
    configs = get_configs()
    print(f"Found {len(configs)} raw configs.")

    print("Ping testing configs...")
    tested_configs = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(test_config, configs)
        for config, ping_time in results:
            if ping_time != float('inf'):
                tested_configs.append((config, ping_time))

    # مرتب سازی بر اساس کمترین پینگ
    tested_configs.sort(key=lambda x: x[1])
    
    # انتخاب 50 کانفیگ برتر
    top_50 = [c[0] for c in tested_configs[:50]]
    
    print(f"Saving top {len(top_50)} configs.")
    
    # ذخیره به صورت متن ساده
    plain_text = "\n".join(top_50)
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(plain_text)
        
    # ذخیره به صورت Base64
    base64_text = base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')
    with open("sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(base64_text)
        
    print("Done!")

if __name__ == "__main__":
    main()
