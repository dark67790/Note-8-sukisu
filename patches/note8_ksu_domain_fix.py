#!/usr/bin/env python3
# note8_ksu_domain_fix.py — fallback SID match for u:r:su:s0
# Root cause: security_secctx_to_secid(KERNEL_SU_CONTEXT, ...) returns
# sid=0, error=-22 (EINVAL) at boot on Note 8 — confirmed via dmesg:
#   "KernelSU: security_secctx_to_secid u:r:ksu:s0 -> sid: 0, error: -22"
# The "ksu" SELinux type is never declared in this device's loaded policy
# (Samsung 4.4 monolithic sepolicy, not Treble split-policy like GKI/Fold4).
# Confirmed: granted-root Termux shell shows /proc/self/attr/current ==
# "u:r:su:s0", not "u:r:ksu:s0". susfs_ksu_sid (susfs.c side) is unused —
# only is_task_ksu_domain() needs patching.

import re, os, sys

def fix(path, old, new, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found — SKIP")
        return False
    if old not in s:
        print(f"⚠️  {label}: anchor not found — already applied or mismatch")
        return False
    if new in s:
        print(f"↩️  {label}: already applied — SKIP")
        return True
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")
    return True

SEL = 'KernelSU/kernel/selinux/selinux.c'

print("══ KernelSU/kernel/selinux/selinux.c — Note 8 ksu-domain fallback ══")

fix(SEL,
    'static u32 cached_su_sid __read_mostly = 0;',
    'static u32 cached_su_sid __read_mostly = 0;\n'
    'static u32 cached_legacy_su_sid __read_mostly = 0; // Note 8: fallback for u:r:su:s0',
    'selinux.c: add cached_legacy_su_sid declaration')

fix(SEL,
    '    err = security_secctx_to_secid(KERNEL_SU_CONTEXT, strlen(KERNEL_SU_CONTEXT), &cached_su_sid);\n'
    '    if (err) {\n'
    '        pr_warn("Failed to cache kernel su domain SID: %d\\n", err);\n'
    '        cached_su_sid = 0;\n'
    '    } else {\n'
    '        pr_info("Cached su SID: %u\\n", cached_su_sid);\n'
    '    }',
    '    err = security_secctx_to_secid(KERNEL_SU_CONTEXT, strlen(KERNEL_SU_CONTEXT), &cached_su_sid);\n'
    '    if (err) {\n'
    '        pr_warn("Failed to cache kernel su domain SID: %d\\n", err);\n'
    '        cached_su_sid = 0;\n'
    '    } else {\n'
    '        pr_info("Cached su SID: %u\\n", cached_su_sid);\n'
    '    }\n'
    '\n'
    '    err = security_secctx_to_secid("u:r:su:s0", strlen("u:r:su:s0"), &cached_legacy_su_sid);\n'
    '    if (err) {\n'
    '        pr_warn("Failed to cache legacy su domain SID: %d\\n", err);\n'
    '        cached_legacy_su_sid = 0;\n'
    '    } else {\n'
    '        pr_info("Cached legacy su SID: %u\\n", cached_legacy_su_sid);\n'
    '    }',
    'selinux.c: cache fallback u:r:su:s0 SID in cache_sid()')

fix(SEL,
    'bool is_task_ksu_domain(const struct cred *cred)\n'
    '{\n'
    '    return is_sid_match(cred, cached_su_sid, KERNEL_SU_CONTEXT);\n'
    '}',
    'bool is_task_ksu_domain(const struct cred *cred)\n'
    '{\n'
    '    if (is_sid_match(cred, cached_su_sid, KERNEL_SU_CONTEXT))\n'
    '        return true;\n'
    '    if (cached_legacy_su_sid)\n'
    '        return is_sid_match(cred, cached_legacy_su_sid, "u:r:su:s0");\n'
    '    return false;\n'
    '}',
    'selinux.c: is_task_ksu_domain() — accept u:r:su:s0 fallback')

print("\nDone.")