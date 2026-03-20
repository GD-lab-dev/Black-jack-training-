pip install -r requirements.txt

if command -v python3 >/dev/null 2>&1; then
    python3 new_chat_main.py
else
    python new_chat_main.py
fi
