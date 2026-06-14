#!/usr/bin/env python3
# manual_hooks.py — ReSukiSU manual hooks for non-GKI 4.4 (SUSFS Inline Hook Mode)
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
        print(f"⚠️  {label}: pattern not found")
        return
    with open(path, 'w') as f:
        f.write(re.sub(pattern, replacement, s, count=1, flags=re.DOTALL))
    print(f"✅ {label}")

# ── fs/exec.c ──────────────────────────────────────────────────────────────
print("── fs/exec.c ────────────────────────────────────────────────────────")

fix('fs/exec.c',
    'static int do_execveat_common(int fd, struct filename *filename,',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n'
    '\t\t\tvoid *argv, void *envp, int *flags);\n'
    '#endif\n'
    'static int do_execveat_common(int fd, struct filename *filename,',
    'exec.c: externs')

fix('fs/exec.c',
    '\tint retval;\n\n\tif (IS_ERR(filename))',
    '\tint retval;\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);\n'
    '#endif\n\n'
    '\tif (IS_ERR(filename))',
    'exec.c: hook')

# ── fs/open.c ──────────────────────────────────────────────────────────────
print("\n── fs/open.c ────────────────────────────────────────────────────────")

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
print("\n── fs/stat.c ────────────────────────────────────────────────────────")

fix('fs/stat.c',
    'int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);\n'
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

# ── kernel/reboot.c ────────────────────────────────────────────────────────
print("\n── kernel/reboot.c ──────────────────────────────────────────────────")

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

# ── kernel/sys.c ───────────────────────────────────────────────────────────
print("\n── kernel/sys.c ─────────────────────────────────────────────────────")

fix('kernel/sys.c',
    'SYSCALL_DEFINE3(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid)\n'
    '{\n'
    '\tstruct user_namespace *ns = current_user_ns();\n'
    '\tconst struct cred *old;\n'
    '\tstruct cred *new;\n'
    '\tint retval;\n'
    '\tkuid_t kruid, keuid, ksuid;\n'
    '\n'
    '\tkruid = make_kuid(ns, ruid);',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_setresuid(uid_t *ruid, uid_t *euid, uid_t *suid);\n'
    '#endif\n'
    'SYSCALL_DEFINE3(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid)\n'
    '{\n'
    '\tstruct user_namespace *ns = current_user_ns();\n'
    '\tconst struct cred *old;\n'
    '\tstruct cred *new;\n'
    '\tint retval;\n'
    '\tkuid_t kruid, keuid, ksuid;\n'
    '\n'
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_setresuid(&ruid, &euid, &suid);\n'
    '#endif\n'
    '\tkruid = make_kuid(ns, ruid);',
    'sys.c: ksu_handle_setresuid hook')

# ── fs/read_write.c ────────────────────────────────────────────────────────
print("\n── fs/read_write.c ──────────────────────────────────────────────────")

fix('fs/read_write.c',
    'SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)\n'
    '{\n'
    '\tstruct fd f = fdget_pos(fd);\n'
    '\tssize_t ret = -EBADF;',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_sys_read(unsigned int *fd, char __user **buf, size_t *count);\n'
    '#endif\n'
    'SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)\n'
    '{\n'
    '\tstruct fd f = fdget_pos(fd);\n'
    '\tssize_t ret = -EBADF;\n'
    '#ifdef CONFIG_KSU\n'
    '\tksu_handle_sys_read(&fd, &buf, &count);\n'
    '#endif',
    'read_write.c: ksu_handle_sys_read hook')

# ── drivers/input/input.c ──────────────────────────────────────────────────
print("\n── drivers/input/input.c ────────────────────────────────────────────")

fix('drivers/input/input.c',
    '\tint disposition;\n'
    '\n'
    '\tdisposition = input_get_disposition(dev, type, code, &value);',
    '\tint disposition;\n'
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);\n'
    '\tksu_handle_input_handle_event(&type, &code, &value);\n'
    '#endif\n'
    '\n'
    '\tdisposition = input_get_disposition(dev, type, code, &value);',
    'input.c: ksu_handle_input_handle_event hook')

print("\n✅ All ReSukiSU manual hooks applied")
