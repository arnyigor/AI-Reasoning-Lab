import time
import psutil
import pandas as pd
import lmstudio as lms

# ================= НАСТРОЙКИ =================
MODEL_FAST_ID = "unsloth/gpt-oss-20b"
MODEL_SMART_ID = "qwen3-next-80b-a3b-thinking"
PROMPT = "Explain the theory of relativity briefly."

# ================= GPU MONITORING =================
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False
    print("⚠️ GPU monitoring disabled")

def get_metrics():
    res = {'ram_gb': round(psutil.virtual_memory().used / (1024**3), 2), 'vram_gb': 0}
    if GPU_AVAILABLE:
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            res['vram_gb'] = round(pynvml.nvmlDeviceGetMemoryInfo(h).used / (1024**3), 2)
        except: pass
    return res

def run_test_scenario(client, model_id, label, config_overrides=None):
    print(f"\n   ⏱️  Test: {label}")

    try:
        if config_overrides:
            model = client.llm.model(model_id, config=config_overrides)
        else:
            model = client.llm.model(model_id)
    except Exception as e:
        print(f"      ❌ Load Error: {e}")
        return None

    pre = get_metrics()
    print(f"      [Start] RAM: {pre['ram_gb']}GB | VRAM: {pre['vram_gb']}GB")

    start = time.time()
    t_first = None
    count = 0

    try:
        stream = model.respond_stream(PROMPT)
        print("      Generating", end="", flush=True)
        for chunk in stream:
            if t_first is None: t_first = time.time()
            content = None
            if isinstance(chunk, dict): content = chunk.get("content")
            elif hasattr(chunk, "content"): content = chunk.content

            if content:
                count += 1
                if count % 10 == 0: print(".", end="", flush=True)

        end = time.time()
        ttft = (t_first - start) * 1000 if t_first else 0
        speed = count / (end - t_first) if t_first else 0
        post = get_metrics()

        print(f" Done. ({speed:.1f} t/s)")
        return {
            "Scenario": label,
            "TTFT (ms)": round(ttft, 1),
            "Speed (t/s)": round(speed, 2),
            "RAM (GB)": post['ram_gb'],
            "VRAM (GB)": post['vram_gb']
        }

    except Exception as e:
        print(f"\n      ❌ Runtime Error: {e}")
        return None

def main():
    print("⏳ Connecting to 127.0.0.1:1234 ...")
    try:
        # 1. Явно указываем адрес через ws:// (веб-сокет)
        # Это обходит механизм поиска lock-файлов, который у тебя сбоит
        client = lms.Client()

        # 2. Не пытаемся читать client.api_host сразу — это ленивое свойство
        # Вместо этого проверяем связь действием
        print("   Checking connection...")
        models = client.llm.list_loaded()

        print(f"✅ Connected! Models loaded: {len(models)}")

    except Exception as e:
        print(f"⛔ Connection failed: {e}")
        # Если всё равно ошибка — проверяем, что порт реально открыт
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 1234))
        if result == 0:
            print("   -> Port 1234 is OPEN (System visible). Problem is in SDK syntax.")
        else:
            print("   -> Port 1234 is CLOSED. Check LM Studio Server Settings.")
        return

    results = []

    # 0. CLEANUP
    print("\n🧹 Unloading all models...")
    for m in client.llm.list_loaded(): m.unload()
    time.sleep(1)

    # 1. PHASE 1: FAST (GPU)
    res = run_test_scenario(client, MODEL_FAST_ID, "Fast (Solo)", {"gpu_offload_ratio": 1.0})
    if res: results.append(res)

    for m in client.llm.list_loaded(): m.unload()

    # 2. PHASE 2: SMART (RAM)
    res = run_test_scenario(client, MODEL_SMART_ID, "Smart (Solo)", {"gpu_offload_ratio": 0.0})
    if res: results.append(res)

    print("      ⚠️ Smart model left in RAM...")

    # 3. PHASE 3: STRESS
    print("\n🧪 Starting Stress Test...")
    res = run_test_scenario(client, MODEL_FAST_ID, "Fast (Under Load)", {"gpu_offload_ratio": 1.0})
    if res: results.append(res)

    if results:
        print("\n\n📊 RESULTS:\n", pd.DataFrame(results).to_markdown(index=False))

if __name__ == "__main__":
    main()
