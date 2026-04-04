import sys, os
sys.path.append('.')
from main import load_conversation
res = load_conversation('dd2e7fb6-9d71-4e74-a1d1-bc6bbd6d7e9e')
print("Loaded length:", len(res))
if len(res) > 0:
    print("Roles:")
    for m in res:
        print(" -", m["role"])
