#!/usr/bin/env python3
# manual_hooks.py — ReSukiSU manual hooks for non-GKI 4.4
# Run from kernel_source/

import re

def fix(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: context not found")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

def fix_regex(path, pattern, replacement, label):
    with open(path, 'r') as f:
        s = f.read()
    if not re.search(pattern, s, re.DOTALL):
        print(f"⚠️  {label}: pattern context not found")
        return
    with open(path, 'w') as f:
        f.write(re.sub(pattern, replacement, s, count=1, flags=re.DOTALL))
    print(f"✅ {label}")

# ── fs/exec.c ──────────────────────────────────────────────────────────────
fix('fs/exec.c',
    'static int do_execveat_common(int fd, struct filename *filename,',
    '#ifdef CONFIG_KSU\n'
    'extern bool ksu_execveat_hook __read_mostly;\n'
    'extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n'
    '\t\t\tvoid *argv, void *envp, int *flags);\n'
    'extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,\n'
    '\t\t\tvoid *argv, void *envp, int *flags);\n'
    '#endif\n'
    'static int do_execveat_common(int fd, struct filename *filename,',
    'exec.c: externs')

fix('fs/exec.c',
    '\tint retval;\n\n\tif (IS_ERR(filename))',
    '\tint retval;\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tif (unlikely(ksu_execveat_hook))\n'
    '\t\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);\n'
    '\telse\n'
    '\t\tksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);\n'
    '#endif\n\n'
    '\tif (IS_ERR(filename))',
    'exec.c: hook')

# ── fs/open.c ──────────────────────────────────────────────────────────────
fix('fs/open.c',
    'SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n'
    '\t\t\tint *mode, int *flags);\n'
    '#endif\n'
    'SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)',
    'open.c: externs')

fix('fs/open.c',
    '\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n\n\tif (mode & ~S_IRWXO)',
    '\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n'
    '#endif\n\n'
    '\tif (mode & ~S_IRWXO)',
    'open.c: hook')

# ── fs/stat.c ──────────────────────────────────────────────────────────────
fix('fs/stat.c',
    'int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);\n'
    'extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);\n'
    'extern void ksu_handle_fstat64_ret(unsigned long *fd, struct stat64 __user **statbuf_ptr);\n'
    '#endif\n'
    'int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,',
    'stat.c: externs')

fix('fs/stat.c',
    '\tunsigned int lookup_flags = 0;\n\n\tif ((flag & ~(AT_SYMLINK_NOFOLLOW',
    '\tunsigned int lookup_flags = 0;\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_stat(&dfd, &filename, &flag);\n'
    '#endif\n\n'
    '\tif ((flag & ~(AT_SYMLINK_NOFOLLOW',
    'stat.c: ksu_handle_stat hook')

# Anchored to the exact system call definitions to prevent function-bleeding
fix_regex('fs/stat.c',
          r'(SYSCALL_DEFINE2\s*\(\s*newfstat\s*,.*?cp_new_stat\s*\(\s*&stat\s*,\s*statbuf\s*\);)',
          r'\1\n#ifdef CONFIG_KSU\n\tksu_handle_newfstat_ret(&fd, &statbuf);\n#endif',
          'stat.c: ksu_handle_newfstat_ret hook (targeted)')

fix_regex('fs/stat.c',
          r'(SYSCALL_DEFINE2\s*\(\s*fstat64\s*,.*?cp_new_stat64\s*\(\s*&stat\s*,\s*statbuf\s*\);)',
          r'\1\n#ifdef CONFIG_KSU\n\tksu_handle_fstat64_ret(&fd, &statbuf);\n#endif',
          'stat.c: ksu_handle_fstat64_ret hook (targeted)')

# ── kernel/reboot.c ────────────────────────────────────────────────────────
fix('kernel/reboot.c',
    'SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_sys_reboot(int magic1, int magic2,\n'
    '\t\t\tunsigned int cmd, void __user **arg);\n'
    '#endif\n'
    'SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,',
    'reboot.c: externs')

fix('kernel/reboot.c',
    '\tif (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))',
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n'
    '#endif\n\n'
    '\tif (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))',
    'reboot.c: hook')

print("\n✅ All ReSukiSU manual hooks applied")
