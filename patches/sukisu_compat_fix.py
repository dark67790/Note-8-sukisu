#!/usr/bin/env python3
# sukisu_compat_fix.py — SukiSU 4.4 ARM64 compatibility fixes
# Run from kernel_source/

def fix(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: not found — already applied or source changed")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

# Fix 1: ARM64 syscall_fn_t typedef missing in syscall_hook.h
fix('drivers/kernelsu/hook/syscall_hook.h',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n#endif',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n'
    '#elif defined(__aarch64__)\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n'
    '#else\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n#endif',
    'syscall_hook.h: ARM64 syscall_fn_t typedef')

# Fix 2: MODULE_IMPORT_NS doesn't exist before 5.4
fix('drivers/kernelsu/core/init.c',
    'MODULE_IMPORT_NS(',
    '#ifndef MODULE_IMPORT_NS\n#define MODULE_IMPORT_NS(ns)\n#endif\nMODULE_IMPORT_NS(',
    'init.c: MODULE_IMPORT_NS compat')

print("\n✅ All SukiSU 4.4 fixes applied")
