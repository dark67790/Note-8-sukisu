#!/usr/bin/env python3
# manual_hooks.py — KSU manual hooks for non-GKI 4.4
# Run from kernel_source/

def fix(path, old, new, label):
    with open(path, 'r') as f:
        s = f.read()
    if old not in s:
        print(f"⚠️  {label}: context not found")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
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

# ── fs/read_write.c ────────────────────────────────────────────────────────
fix('fs/read_write.c',
    'ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)\n{',
    '#ifdef CONFIG_KSU\n'
    'extern bool ksu_vfs_read_hook __read_mostly;\n'
    'extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,\n'
    '\t\t\tsize_t *count_ptr, loff_t **pos);\n'
    '#endif\n'
    'ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)\n{',
    'read_write.c: externs')

fix('fs/read_write.c',
    '\tssize_t ret;\n\n\tif (!(file->f_mode & FMODE_READ))',
    '\tssize_t ret;\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tif (unlikely(ksu_vfs_read_hook))\n'
    '\t\tksu_handle_vfs_read(&file, &buf, &count, &pos);\n'
    '#endif\n'
    '\tif (!(file->f_mode & FMODE_READ))',
    'read_write.c: hook')

# ── fs/stat.c ──────────────────────────────────────────────────────────────
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
    'stat.c: hook')

# ── drivers/input/input.c ──────────────────────────────────────────────────
fix('drivers/input/input.c',
    'static void input_handle_event(struct input_dev *dev,\n'
    '                               unsigned int type, unsigned int code, int value)\n{',
    '#ifdef CONFIG_KSU\n'
    'extern bool ksu_input_hook __read_mostly;\n'
    'extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);\n'
    '#endif\n'
    'static void input_handle_event(struct input_dev *dev,\n'
    '                               unsigned int type, unsigned int code, int value)\n{',
    'input.c: externs')

fix('drivers/input/input.c',
    '\tdisposition = input_get_disposition(dev, type, code, &value);\n',
    '\tdisposition = input_get_disposition(dev, type, code, &value);\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tif (unlikely(ksu_input_hook))\n'
    '\t\tksu_handle_input_handle_event(&type, &code, &value);\n'
    '#endif\n',
    'input.c: hook')

# ── kernel/reboot.c ────────────────────────────────────────────────────────
fix('kernel/reboot.c',
    'SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,',
    '#ifdef CONFIG_KSU\n'
    'extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,\n'
    '\t\t\tvoid __user **arg);\n'
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

# ── security/selinux/hooks.c ───────────────────────────────────────────────
fix('security/selinux/hooks.c',
    'static int check_nnp_nosuid(const struct linux_binprm *bprm,',
    '#ifdef CONFIG_KSU\n'
    'extern bool is_ksu_transition(const struct task_security_struct *old_tsec,\n'
    '\t\t\t      const struct task_security_struct *new_tsec);\n'
    '#endif\n'
    'static int check_nnp_nosuid(const struct linux_binprm *bprm,',
    'selinux/hooks.c: externs')

fix('security/selinux/hooks.c',
    '\tif (new_tsec->sid == old_tsec->sid)\n\t\treturn 0; /* No change in credentials */\n',
    '\tif (new_tsec->sid == old_tsec->sid)\n\t\treturn 0; /* No change in credentials */\n\n'
    '#ifdef CONFIG_KSU\n'
    '\tif (is_ksu_transition(old_tsec, new_tsec))\n'
    '\t\treturn 0;\n'
    '#endif\n',
    'selinux/hooks.c: hook')

print("\n✅ All manual hooks applied")
