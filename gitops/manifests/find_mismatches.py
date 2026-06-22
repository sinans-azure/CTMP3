import os
import re

manifests_dir = r"c:\Users\ixvpr\CTMP3\gitops\manifests"

services = [d for d in os.listdir(manifests_dir) if os.path.isdir(os.path.join(manifests_dir, d))]

def get_values_keys(filepath):
    keys = set()
    stack = []
    with open(filepath, "r") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            
            # Find key
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*:', stripped)
            if not match:
                continue
            key = match.group(1)
            
            # Adjust stack based on indentation
            while stack and stack[-1][0] >= indent:
                stack.pop()
            
            stack.append((indent, key))
            full_key = ".".join([item[1] for item in stack])
            keys.add(full_key)
    return keys

for svc in services:
    svc_dir = os.path.join(manifests_dir, svc)
    values_path = os.path.join(svc_dir, "values.yaml")
    if not os.path.exists(values_path):
        continue
    
    print(f"\n--- Checking service: {svc} ---")
    values_keys = get_values_keys(values_path)
    print(f"Values keys ({len(values_keys)}): {sorted(list(values_keys))}")
    
    templates_dir = os.path.join(svc_dir, "templates")
    if not os.path.exists(templates_dir):
        continue
        
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if not file.endswith(".yaml") and not file.endswith(".tpl"):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                content = f.read()
            
            # Find references to .Values
            matches = re.findall(r'\.Values\.([a-zA-Z0-9_\.\-]+)', content)
            unique_matches = sorted(list(set(matches)))
            print(f"  [{file}] Found matches: {unique_matches}")
            for m in unique_matches:
                m_clean = re.split(r'[^a-zA-Z0-9_\.\-]', m)[0]
                m_clean = m_clean.strip(".")
                if m_clean not in values_keys:
                    print(f"  [{file}] MISSING: .Values.{m_clean}")
