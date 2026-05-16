#!/usr/bin/env python3
# sukisu_compat_fix.py — SukiSU 4.4 ARM64 compatibility fixes
# Run from kernel_source/

import glob, re

def fix(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: not found")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

def fix_all(old, new, label):
    count = 0
    for path in glob.glob('drivers/kernelsu/**/*', recursive=True):
        try:
            with open(path, 'r') as f:
                s = f.read()
            if old not in s:
                continue
            with open(path, 'w') as f:
                f.write(s.replace(old, new))
            count += 1
        except (IsADirectoryError, UnicodeDecodeError):
            continue
    print(f"{'✅' if count else '⚠️ '} {label} ({count} file(s))")

# ── Fix 1: ARM64 syscall_fn_t typedef ──────────────────────────────────────
fix('drivers/kernelsu/hook/syscall_hook.h',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n#endif',
    '#if defined(__x86_64__)\ntypedef sys_call_ptr_t syscall_fn_t;\n'
    '#elif defined(__aarch64__)\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n'
    '#else\ntypedef asmlinkage long (*syscall_fn_t)(const struct pt_regs *);\n#endif',
    'syscall_hook.h: ARM64 syscall_fn_t')

# ── Fix 2: MODULE_IMPORT_NS doesn't exist before 5.4 ──────────────────────
def fix_module_import_ns(path):
    with open(path, 'r') as f:
        s = f.read()
    new_s = re.sub(r'^MODULE_IMPORT_NS\([^)]*\);\n?', '', s, flags=re.MULTILINE)
    changed = new_s != s
    if changed:
        with open(path, 'w') as f:
            f.write(new_s)
    print(f"{'✅' if changed else '⚠️ '} init.c: MODULE_IMPORT_NS removed")

fix_module_import_ns('drivers/kernelsu/core/init.c')

# ── Fix 3: compiler_types.h → compiler.h (split in 4.20) ──────────────────
fix_all('#include <linux/compiler_types.h>',
        '#include <linux/compiler.h>',
        'compiler_types.h → compiler.h')

# ── Fix 4: pgtable.h → asm/pgtable.h (linux/pgtable.h added in 5.8) ───────
fix_all('#include <linux/pgtable.h>',
        '#include <asm/pgtable.h>',
        'pgtable.h → asm/pgtable.h')

# ── Fix 5: sched/* split from sched.h in 4.11 ─────────────────────────────
fix_all('#include <linux/sched/signal.h>',    '#include <linux/sched.h>', 'sched/signal.h → sched.h')
fix_all('#include <linux/sched/task.h>',      '#include <linux/sched.h>', 'sched/task.h → sched.h')
fix_all('#include <linux/sched/task_stack.h>','#include <linux/sched.h>', 'sched/task_stack.h → sched.h')
fix_all('#include <linux/sched/user.h>',      '#include <linux/sched.h>', 'sched/user.h → sched.h')

# Targeted fix for sucompat.c in case fix_all missed it
fix('drivers/kernelsu/feature/sucompat.c',
    '#include <linux/sched/task_stack.h>',
    '#include <linux/sched.h>',
    'sucompat.c: task_stack.h targeted fix')

# ── Fix 6: minmax.h → kernel.h (added in 5.15) ────────────────────────────
fix_all('#include <linux/minmax.h>', '#include <linux/kernel.h>', 'minmax.h → kernel.h')

# ── Fix 7: overflow.h → kernel.h (added in 4.13) ──────────────────────────
fix_all('#include <linux/overflow.h>', '#include <linux/kernel.h>', 'overflow.h → kernel.h')

# ── Fix 8: hex.h → kernel.h ───────────────────────────────────────────────
fix_all('#include <linux/hex.h>', '#include <linux/kernel.h>', 'hex.h → kernel.h')

# ── Fix 9: input-event-codes.h → input.h ──────────────────────────────────
fix_all('#include <linux/input-event-codes.h>', '#include <linux/input.h>', 'input-event-codes.h → input.h')

# ── Fix 10: set_memory.h → asm/set_memory.h (added in 5.2) ───────────────
fix_all('#include <linux/set_memory.h>', '#include <asm/set_memory.h>', 'set_memory.h → asm/set_memory.h')

# ── Fix 11: p4d_t doesn't exist before 4.12 ───────────────────────────────
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
path = 'drivers/kernelsu/hook/arm64/patch_memory.c'
with open(path, 'r') as f:
    s = f.read()
if 'KERNEL_VERSION(4, 12, 0)' not in s:
    with open(path, 'w') as f:
        f.write(p4d_compat + s)
    print('✅ patch_memory.c: p4d_t compat')
else:
    print('⚠️  patch_memory.c: p4d_t already patched')

# ── Fix 12: copy_to_kernel_nofault → probe_kernel_write (added in 5.8) ────
fix('drivers/kernelsu/hook/arm64/patch_memory.c',
    'copy_to_kernel_nofault(map, src, len)',
    'probe_kernel_write(map, src, len)',
    'patch_memory.c: copy_to_kernel_nofault → probe_kernel_write')

# ── Fix 13: copy_from_user_nofault → copy_from_user (doesn't exist in 4.4)─
fix('drivers/kernelsu/kernel_compat.h',
    'copy_from_user_nofault(to, from, count)',
    'copy_from_user(to, from, count)',
    'kernel_compat.h: copy_from_user_nofault → copy_from_user')

# ── Fix 14: PT_REGS_ORIG_SYSCALL doesn't exist in 4.4 ARM64 ───────────────
pt_regs_compat = (
    '#ifndef PT_REGS_ORIG_SYSCALL\n'
    '#define PT_REGS_ORIG_SYSCALL(regs) ((regs)->syscallno)\n'
    '#endif\n\n'
)
path = 'drivers/kernelsu/hook/arm64/syscall_hook.c'
with open(path, 'r') as f:
    s = f.read()
if 'PT_REGS_ORIG_SYSCALL' in s and 'define PT_REGS_ORIG_SYSCALL' not in s:
    with open(path, 'w') as f:
        f.write(pt_regs_compat + s)
    print('✅ syscall_hook.c: PT_REGS_ORIG_SYSCALL compat')
else:
    print('⚠️  syscall_hook.c: PT_REGS_ORIG_SYSCALL already handled')

# ── Fix 15: __nocfi not defined in GCC 8 / 4.4 kernels ───────────────────
fix_all('__nocfi ', '', '__nocfi stripped')

print("\n✅ All SukiSU 4.4 compat fixes applied")

# Fix 16: strncpy_from_user_nofault → strncpy_from_user (added in 5.8)
fix_all('strncpy_from_user_nofault', 'strncpy_from_user', 'strncpy_from_user_nofault → strncpy_from_user')
