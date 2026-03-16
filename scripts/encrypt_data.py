"""
AES-256-GCM 加密脚本
将 data/processed/*.json 加密后输出到 docs/data/*.enc
使用 PBKDF2-SHA256 派生密钥，与前端 Web Crypto API 保持一致
"""
import base64
import os
import sys

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256, HMAC
from Crypto.Random import get_random_bytes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "..")
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(ROOT_DIR, "docs", "data")


def encrypt_file(input_path, output_path, password):
    with open(input_path, "r", encoding="utf-8") as f:
        plaintext = f.read().encode("utf-8")

    salt = get_random_bytes(16)
    # PBKDF2-SHA256, 10000 iterations - 与前端 Web Crypto 一致
    key = PBKDF2(password.encode("utf-8"), salt, dkLen=32, count=10000,
                 prf=lambda p, s: HMAC.new(p, s, SHA256).digest())

    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)

    # 输出格式: base64(salt[16] + nonce[16] + tag[16] + ciphertext)
    payload = salt + cipher.nonce + tag + ciphertext
    encoded = base64.b64encode(payload).decode("ascii")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(encoded)

    return len(plaintext), len(encoded)


def main():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        print("[ERROR] 请设置环境变量 DASHBOARD_PASSWORD", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".json")]
    if not json_files:
        print("[ERROR] data/processed/ 中没有JSON文件", file=sys.stderr)
        sys.exit(1)

    print(f"加密 {len(json_files)} 个文件, 密码长度: {len(password)}")
    for filename in json_files:
        input_path = os.path.join(PROCESSED_DIR, filename)
        output_name = filename.replace(".json", ".enc")
        output_path = os.path.join(OUTPUT_DIR, output_name)

        plain_size, enc_size = encrypt_file(input_path, output_path, password)
        print(f"  [OK] {filename} ({plain_size}B) -> {output_name} ({enc_size}B)")

    print(f"\n[DONE] 加密完成, 输出到 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
