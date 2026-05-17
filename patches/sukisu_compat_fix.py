#!/usr/bin/env python3
# sukisu_compat_fix.py — ReSukiSU 4.4 ARM64 compatibility fixes
# Run from kernel_source/

import glob, re, os

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

def fix_file_all(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: not found")
        return
    count = s.count(old)
    with open(path, 'w') as f:
        f.write(s.replace(old, new))
    print(f"✅ {label} ({count} occurrence(s))")

# ── Fix 1: MODULE_IMPORT_NS doesn't exist before 5.4 ──────────────────────
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

# ── Fix 2: compiler_types.h → compiler.h (split in 4.20) ──────────────────
fix_all('#include <linux/compiler_types.h>',
        '#include <linux/compiler.h>',
        'compiler_types.h → compiler.h')

# ── Fix 3: pgtable.h → asm/pgtable.h (linux/pgtable.h added in 5.8) ───────
fix_all('#include <linux/pgtable.h>',
        '#include <asm/pgtable.h>',
        'pgtable.h → asm/pgtable.h')

# ── Fix 4: sched/* split from sched.h in 4.11 ─────────────────────────────
fix_all('#include <linux/sched/signal.h>',     '#include <linux/sched.h>', 'sched/signal.h → sched.h')
fix_all('#include <linux/sched/task.h>',       '#include <linux/sched.h>', 'sched/task.h → sched.h')
fix_all('#include <linux/sched/task_stack.h>', '#include <linux/sched.h>', 'sched/task_stack.h → sched.h')
fix_all('#include <linux/sched/user.h>',       '#include <linux/sched.h>', 'sched/user.h → sched.h')

# ── Fix 5: minmax.h → kernel.h (added in 5.15) ────────────────────────────
fix_all('#include <linux/minmax.h>', '#include <linux/kernel.h>', 'minmax.h → kernel.h')

# ── Fix 6: overflow.h → kernel.h (added in 4.13) ──────────────────────────
fix_all('#include <linux/overflow.h>', '#include <linux/kernel.h>', 'overflow.h → kernel.h')

# ── Fix 7: hex.h → kernel.h ───────────────────────────────────────────────
fix_all('#include <linux/hex.h>', '#include <linux/kernel.h>', 'hex.h → kernel.h')

# ── Fix 8: input-event-codes.h → input.h ──────────────────────────────────
fix_all('#include <linux/input-event-codes.h>', '#include <linux/input.h>', 'input-event-codes.h → input.h')

# ── Fix 9: set_memory.h → asm/set_memory.h (added in 5.2) ────────────────
fix_all('#include <linux/set_memory.h>', '#include <asm/set_memory.h>', 'set_memory.h → asm/set_memory.h')

# ── Fix 10: patch_memory.c — p4d_t + __pte_to_phys + icache compat ────────
path = 'drivers/kernelsu/hook/arm64/patch_memory.c'
try:
    with open(path, 'r') as f:
        s = f.read()

    compat = (
        '#include <asm-generic/fixmap.h>\n\n'
        '#include <linux/version.h>\n'
        '#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 12, 0)\n'
        'typedef pgd_t p4d_t;\n'
        'static inline p4d_t *p4d_offset(pgd_t *pgd, unsigned long addr) { return (p4d_t *)pgd; }\n'
        'static inline int p4d_none(p4d_t p4d) { return 0; }\n'
        'static inline int p4d_bad(p4d_t p4d) { return 0; }\n'
        '#define p4d_val(x) pgd_val(*((pgd_t *)&(x)))\n'
        '#endif\n'
        '#ifndef __pte_to_phys\n'
        '#define __pte_to_phys(pte) (pte_pfn(pte) << PAGE_SHIFT)\n'
        '#endif\n'
        '#ifndef __flush_icache_range\n'
        '#define __flush_icache_range flush_icache_range\n'
        '#endif\n'
    )

    anchor = '#include <asm-generic/fixmap.h>'
    if anchor in s and 'KERNEL_VERSION(4, 12, 0)' not in s:
        s = s.replace(anchor, compat, 1)
        with open(path, 'w') as f:
            f.write(s)
        print('✅ patch_memory.c: p4d_t + __pte_to_phys + __flush_icache_range compat')
    elif 'KERNEL_VERSION(4, 12, 0)' in s:
        print('⚠️  patch_memory.c: already patched')
    else:
        print('⚠️  patch_memory.c: anchor not found')
except FileNotFoundError:
    print('⚠️  patch_memory.c: not found')

# ── Fix 11: copy_from_user_nofault + copy_to_user_nofault (added in 5.8) ──
fix_file_all('drivers/kernelsu/runtime/ksud_integration.c',
    'copy_from_user_nofault(',
    'copy_from_user(',
    'ksud_integration.c: copy_from_user_nofault → copy_from_user')

fix_file_all('drivers/kernelsu/runtime/ksud_integration.c',
    'copy_to_user_nofault(',
    'copy_to_user(',
    'ksud_integration.c: copy_to_user_nofault → copy_to_user')

print("\n✅ All ReSukiSU 4.4 compat fixes applied")
