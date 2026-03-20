if command -v pip3 >/dev/null 2>&1; then
    pip3 install -r requirements.txt
else
    pip install -r requirements.txt
fi

if command -v python3 >/dev/null 2>&1; then
    python3 new_chat_main.py
else
    python new_chat_main.py
fi
