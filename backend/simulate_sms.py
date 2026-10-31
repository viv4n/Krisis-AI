import requests
import json
import sys

URL = "http://127.0.0.1:8000/api/v1/textbee/webhook"

# Allow custom message from command-line argument if provided during hackathon presentation
default_message = "Urgent: severe flooding trapped 3 people in the basement on Main Street near Memorial Dr"
custom_message = sys.argv[1] if len(sys.argv) > 1 else default_message

payload = {
    "sender": "+17135550199",
    "message": custom_message
}

print(f"[*] Simulating incoming Textbee SMS to: {URL}")
print(f"[*] Payload:\n{json.dumps(payload, indent=2)}")

try:
    response = requests.post(URL, json=payload, timeout=15)
    print("\n[+] Response Status Code:", response.status_code)
    try:
        print("[+] Response Body:\n", json.dumps(response.json(), indent=2))
    except Exception:
        print("[+] Response Body (raw):\n", response.text)
except requests.exceptions.ConnectionError:
    print(f"\n[!] Connection Error: Could not connect to {URL}.")
    print("[!] Please ensure the FastAPI server is running (e.g. `python backend/run.py`).")
    sys.exit(1)
except Exception as e:
    print(f"\n[!] Error during request: {e}")
    sys.exit(1)
