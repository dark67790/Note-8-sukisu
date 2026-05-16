#!/usr/bin/env python3
# sukisu_compat_fix.py — SukiSU 4.4 ARM64 compatibility fixes
# Run from kernel_source/

import glob
import re

def fix(path, old, new, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
        if old not in s:
            print(f"⚠️  {label}: not found — already applied or source changed")
            return
        with open(path, 'w') as f:
            f.write(s.replace(old, new, 1))
        print(f"✅ {label}")
    except FileNotFoundError:
        print(f"❌ {label}: file not found ({path})")

def fix_module_import_ns(path):
    try:
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
    except FileNotFoundError:
        print(f"❌ init.c: file not found ({path})")

def fix_all(old, new, label):
    for path in glob.glob('drivers/kernelsu/**/*', recursive=True):
        try:
            with open(path, 'r') as f:
                s = f.read()
            if old not in s:
                continue
            with open(path, 'w') as f:
                f.write(s.replace(old, new))
            print(f"✅ {label}: {path}")
        except (IsADirectoryError, UnicodeDecodeError):
            continue

# ── Fix 1: ARM64 syscall_fn_t typedef missing in syscall_hook.h ──────────────
fix('drivers/kernelsu/hook/syscall_hook.h',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n#endif',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n'
    '#elif defined(__aarch64__)\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n'
    '#else\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n#endif',
    'syscall_hook.h: ARM64 syscall_fn_t typedef')

# ── Fix 2: MODULE_IMPORT_NS doesn't exist before 5.4 ─────────────────────────
fix_module_import_ns('drivers/kernelsu/core/init.c')

# ── Fix 3: compiler_types.h doesn't exist before 4.20 ────────────────────────
fix_all('#include <linux/compiler_types.h>', '#include <linux/compiler.h>', 'compiler_types.h fix')

# ── Fix 4: linux/pgtable.h doesn't exist before 5.8 ──────────────────────────
fix_all('#include <linux/pgtable.h>', '#include <asm/pgtable.h>', 'pgtable.h fix')

# ── Fix 11: p4d_t doesn't exist before 4.12 ──────────────────────────────────
p4d_compat = (
    '#include <linux/version.h>\n'
    '#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 12, 0)\n'
    'typedef pgd_t p4d_t;\n'
    'static inline p4d_t *p4d_offset(pgd_t *pgd, unsigned long addr) { return (p4d_t *)pgd; }\n'
    'static inline int p4d_none(p4d_t p4d) { return 0; }\n'
    'static inline int p4d_bad(p4d_t p4d) { return 0; }\n'
    '#define p4d_val(x) pgd_val(*((pgd_t *)&(x)))\n'
    '#endif\n\n'
)
path_patch_mem = 'drivers/kernelsu/hook/arm64/patch_memory.c'
try:
    with open(path_patch_mem, 'r') as f:
        s = f.read()
    if 'KERNEL_VERSION(4, 12, 0)' not in s:
        with open(path_patch_mem, 'w') as f:
            f.write(p4d_compat + s)
        print('✅ patch_memory.c: p4d_t compat')
    else:
        print('⚠️  patch_memory.c: p4d_t already patched')
except FileNotFoundError:
    print(f'❌ patch_memory.c: file not found ({path_patch_mem})')

# ── Fix 12: copy_to_kernel_nofault → probe_kernel_write (added in 5.8) ───────
fix('drivers/kernelsu/hook/arm64/patch_memory.c',
    'copy_to_kernel_nofault(map, src, len)',
    'probe_kernel_write(map, src, len)',
    'patch_memory.c: copy_to_kernel_nofault → probe_kernel_write')

# ── Fix 13: copy_from_user_nofault → copy_from_user (doesn't exist in 4.4) ────
fix('drivers/kernelsu/kernel_compat.h',
    'copy_from_user_nofault(to, from, count)',
    'copy_from_user(to, from, count)',
    'kernel_compat.h: copy_from_user_nofault → copy_from_user')

# ── Fix 14: PT_REGS_ORIG_SYSCALL doesn't exist in 4.4 ARM64 ──────────────────
pt_regs_compat = (
    '#ifndef PT_REGS_ORIG_SYSCALL\n'
    '#define PT_REGS_ORIG_SYSCALL(regs) ((regs)->syscallno)\n'
    '#endif\n\n'
)
path_sys_hook = 'drivers/kernelsu/hook/arm64/syscall_hook.c'
try:
    with open(path_sys_hook, 'r') as f:
        s = f.read()
    if 'PT_REGS_ORIG_SYSCALL' in s and 'define PT_REGS_ORIG_SYSCALL' not in s:
        with open(path_sys_hook, 'w') as f:
            f.write(pt_regs_compat + s)
        print('✅ syscall_hook.c: PT_REGS_ORIG_SYSCALL compat')
    else:
        print('⚠️  syscall_hook.c: PT_REGS_ORIG_SYSCALL already handled')
except FileNotFoundError:
    print(f'❌ syscall_hook.c: file not found ({path_sys_hook})')

# ── Fix 15: __nocfi not defined in GCC 8 / 4.4 kernels ───────────────────────
fix_all('__nocfi ', '', '__nocfi stripped')

print("\n✅ All SukiSU 4.4 fixes applied")
