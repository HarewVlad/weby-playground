import tkinter as tk
import requests
import json
import threading

URL = "http://0.0.0.0:8000/v2/studio?stream=true"
HEADERS = {"Content-Type": "application/json"}


def run_request(prompt_text, output_widget):
    def stream():
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt_text}],
            "project_files": [],
            "uploaded_files": [],
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 512
        }

        output_widget.delete(1.0, tk.END)
        aggregated = {
            "content": "",
            "tool_calls": []
        }

        try:
            with requests.post(URL, json=payload, headers=HEADERS, stream=True) as resp:
                for line in resp.iter_lines(decode_unicode=True):
                    line = line.strip()
                    if not line or not line.startswith("{"):
                        continue
                    try:
                        parsed = json.loads(line)

                        print("parsed:", parsed)
                        content = parsed.get("content")
                        tool_calls = parsed.get("tool_calls")

                        if content:
                            if isinstance(content, dict):
                                aggregated["content"] = content
                            else:
                                aggregated["content"] += content

                        if tool_calls:
                            aggregated["tool_calls"].extend(tool_calls)

                    except Exception as e:
                        print("Parsing error:", e)
                        continue

            formatted = json.dumps(aggregated, indent=2, ensure_ascii=False)
            output_widget.insert(tk.END, formatted)
            output_widget.see(tk.END)

        except Exception as e:
            output_widget.insert(tk.END, f"ERROR: {e}")
            output_widget.see(tk.END)

    threading.Thread(target=stream, daemon=True).start()


def start_gui():
    root = tk.Tk()
    root.title("Studio SSE Aggregator")
    root.geometry("1000x700")

    input_label = tk.Label(root, text="Enter Prompt:")
    input_label.pack()

    input_box = tk.Text(root, height=10)
    input_box.pack(fill=tk.X, padx=10)

    output_label = tk.Label(root, text="Aggregated Response:")
    output_label.pack()

    output_box = tk.Text(root, wrap=tk.WORD, font=("Courier", 10))
    output_box.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    run_button = tk.Button(
        root,
        text="Send Request",
        command=lambda: run_request(input_box.get("1.0", tk.END).strip(), output_box)
    )
    run_button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    start_gui()
