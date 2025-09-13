import os
from pathlib import Path

p = Path(r"C:\Users\ATHARVA\mistral_models\Llama-3.1-8B-Instruct")
print("Exists:", p.exists())
if p.exists():
    for f in p.iterdir():
        print(f.name)
else:
    print("Directory missing")
