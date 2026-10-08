# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 10:18:42 2026

@author: gzche
"""

import json
import glob

for path in sorted(glob.glob('theorems/*.jsonl')) + ['theorems.jsonl']:
    try:
        with open(path, encoding='utf-8') as f:
            count = 0
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    count += 1
                except json.JSONDecodeError as e:
                    print(f"❌ {path} 第 {i} 行: {e}")
        print(f"✅ {path}: {count} 条")
    except FileNotFoundError:
        print(f"⚠️  {path} 不存在")