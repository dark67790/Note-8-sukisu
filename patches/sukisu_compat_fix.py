#!/usr/bin/env python3
# sukisu_compat_fix.py — SukiSU 4.4 ARM64 compatibility fixes
# Run from kernel_source/

import re

def fix(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: not found — already applied or source changed")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

def fix_module_import_ns(path):
    with open(path, 'r') as f:
        s = f.read()
    # Strip any lines starting with MODULE_IMPORT_NS(...)
    new_s = re.sub(r'^MODULE_IMPORT_NS\([^)]*\);\n?', '', s, flags=re.MULTILINE)
    if new_s == s:
        print("⚠️  init.c: MODULE_IMPORT_NS not found — already applied or source changed")
        return
    with open(path, 'w') as f:
        f.write(new_s)
    print("✅ init.c: MODULE_IMPORT_NS removed")

# Fix 1: ARM64 syscall_fn_t typedef missing in syscall_hook.h
fix('drivers/kernelsu/hook/syscall_hook.h',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n#endif',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n'
    '#elif defined(__aarch64__)\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n'
    '#else\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n#endif',
    'syscall_hook.h: ARM64 syscall_fn_t typedef')

# Fix 2: MODULE_IMPORT_NS doesn't exist before 5.4 — drop it completely
fix_module_import_ns('drivers/kernelsu/core/init.c')

print("\n✅ All SukiSU 4.4 fixes applied")
