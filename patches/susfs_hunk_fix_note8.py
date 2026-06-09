#!/usr/bin/env python3
# susfs_hunk_fix_note8.py — SUSFS kernel-4.9 → Samsung 4.4 compat fixes
# Run from kernel_source/ after 50_add_susfs_in_kernel-4.9.patch applied

import re, os

def fix(path, old, new, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found")
        return
    if old not in s:
        print(f"⚠️  {label}: anchor not found")
        return
    if new in s:
        print(f"⚠️  {label}: already applied")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

def fix_regex(path, pattern, replacement, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found")
        return
    if not re.search(pattern, s, re.DOTALL):
        print(f"⚠️  {label}: pattern not found")
        return
    with open(path, 'w') as f:
        f.write(re.sub(pattern, replacement, s, count=1, flags=re.DOTALL))
    print(f"✅ {label}")

# ── fs/dcache.c ───────────────────────────────────────────────────────────────
print("── fs/dcache.c ──────────────────────────────────────────────────────")

# Simpler pattern using [^\n]+ to bypass Python 3.12 strict regex checks
fix_regex('fs/dcache.c',
    r'(\*seqp = seq;)\n(\s+)(if \(!dentry_cmp[^\n]+)\n(\s+)(return dentry;)',
    r'\1\n\2\3 {\n'
    r'#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    r'\2if (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    r'\2\tcontinue;\n'
    r'\2}\n'
    r'#endif\n'
    r'\4\5\n'
    r'\2}',
    'dcache.c: __d_lookup_rcu sus_path check')

# ── fs/namei.c ────────────────────────────────────────────────────────────────
print("\n── fs/namei.c ───────────────────────────────────────────────────────")

# hunk #8 — filename_lookup
fix('fs/namei.c',
    '\t\taudit_inode(name, path->dentry, flags & LOOKUP_PARENT);\n'
    '\trestore_nameidata();\n'
    '\tputname(name);\n'
    '\treturn retval;\n'
    '}\n\n'
    '/* Returns 0 and nd will be valid on success',
    '\t\taudit_inode(name, path->dentry, flags & LOOKUP_PARENT);\n'
    '\trestore_nameidata();\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (!retval && path->dentry->d_inode && unlikely(path->dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\tputname(name);\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '#endif\n'
    '\tputname(name);\n'
    '\treturn retval;\n'
    '}\n\n'
    '/* Returns 0 and nd will be valid on success',
    'namei.c: filename_lookup sus_path check')

# hunk #9 — may_delete (Samsung 4.4 lacks HAS_UNMAPPED_ID)
fix('fs/namei.c',
    '\tif (IS_APPEND(dir))\n'
    '\t\treturn -EPERM;\n'
    '\n'
    '\tif (check_sticky(dir, inode) || IS_APPEND(inode) ||\n'
    '\t    IS_IMMUTABLE(inode) || IS_SWAPFILE(inode))\n'
    '\t\treturn -EPERM;',
    '\tif (IS_APPEND(dir))\n'
    '\t\treturn -EPERM;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (unlikely(inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '#endif\n'
    '\n'
    '\tif (check_sticky(dir, inode) || IS_APPEND(inode) ||\n'
    '\t    IS_IMMUTABLE(inode) || IS_SWAPFILE(inode))\n'
    '\t\treturn -EPERM;',
    'namei.c: may_delete sus_path check')

# hunk #10 — may_create (Samsung 4.4 has no struct user_namespace *s_user_ns)
fix('fs/namei.c',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '\taudit_inode_child(dir, child, AUDIT_TYPE_CHILD_CREATE);',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tint error;\n'
    '#endif\n'
    '\taudit_inode_child(dir, child, AUDIT_TYPE_CHILD_CREATE);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (child->d_inode && unlikely(child->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\terror = inode_permission2(mnt, dir, MAY_WRITE | MAY_EXEC);\n'
    '\t\tif (error) {\n'
    '\t\t\treturn error;\n'
    '\t\t}\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '#endif',
    'namei.c: may_create sus_path check')

# hunk #11 — may_open
fix('fs/namei.c',
    '\tif (!inode)\n'
    '\t\treturn -ENOENT;\n'
    '\n'
    '\tswitch (inode->i_mode & S_IFMT) {',
    '\tif (!inode)\n'
    '\t\treturn -ENOENT;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (unlikely(inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '#endif\n'
    '\n'
    '\tswitch (inode->i_mode & S_IFMT) {',
    'namei.c: may_open sus_path check')

# hunk #12 — may_o_create (non-const struct path, starts with int error = directly)
fix('fs/namei.c',
    'static int may_o_create(struct path *dir, struct dentry *dentry, umode_t mode)\n'
    '{\n'
    '\tint error = security_path_mknod(dir, dentry, mode, 0);\n'
    '\tif (error)\n'
    '\t\treturn error;\n'
    '\n'
    '\terror = inode_permission2(dir->mnt, dir->dentry->d_inode, MAY_WRITE | MAY_EXEC);',
    'static int may_o_create(struct path *dir, struct dentry *dentry, umode_t mode)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tint error;\n'
    '\n'
    '\tif (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\terror = inode_permission2(dir->mnt, dir->dentry->d_inode, MAY_WRITE | MAY_EXEC);\n'
    '\t\tif (error) {\n'
    '\t\t\treturn error;\n'
    '\t\t}\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '\terror = security_path_mknod(dir, dentry, mode, 0);\n'
    '#else\n'
    '\tint error = security_path_mknod(dir, dentry, mode, 0);\n'
    '#endif\n'
    '\tif (error)\n'
    '\t\treturn error;\n'
    '\n'
    '\terror = inode_permission2(dir->mnt, dir->dentry->d_inode, MAY_WRITE | MAY_EXEC);',
    'namei.c: may_o_create sus_path check')

# hunk #13 — lookup_open cached positive dentry
fix('fs/namei.c',
    '\t/* Cached positive dentry: will open in f_op->open */\n'
    '\tif (!need_lookup && dentry->d_inode)\n'
    '\t\tgoto out_no_open;',
    '\t/* Cached positive dentry: will open in f_op->open */\n'
    '\tif (!need_lookup && dentry->d_inode) {\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\tif (unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\t\tdput(dentry);\n'
    '\t\t\treturn -ENOENT;\n'
    '\t\t}\n'
    '#endif\n'
    '\t\tgoto out_no_open;\n'
    '\t}',
    'namei.c: lookup_open cached dentry sus_path check')

# hunk #15 — lookup_open after lookup_real
fix('fs/namei.c',
    '\t\tdentry = lookup_real(dir_inode, dentry, nd->flags);\n'
    '\t\tif (IS_ERR(dentry))\n'
    '\t\t\treturn PTR_ERR(dentry);\n'
    '\t}\n'
    '\n'
    '\t/* Negative dentry',
    '\t\tdentry = lookup_real(dir_inode, dentry, nd->flags);\n'
    '\t\tif (IS_ERR(dentry))\n'
    '\t\t\treturn PTR_ERR(dentry);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\tif (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\t\tdput(dentry);\n'
    '\t\t\treturn -ENOENT;\n'
    '\t\t}\n'
    '#endif\n'
    '\t}\n'
    '\n'
    '\t/* Negative dentry',
    'namei.c: lookup_open lookup_real sus_path check')

# hunks #16+#17 — do_filp_open open_redirect
fix('fs/namei.c',
    'struct file *do_filp_open(int dfd, struct filename *pathname,',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern struct filename* susfs_get_redirected_path(unsigned long ino);\n'
    '#endif\n\n'
    'struct file *do_filp_open(int dfd, struct filename *pathname,',
    'namei.c: do_filp_open open_redirect extern')

fix('fs/namei.c',
    '\tset_nameidata(&nd, dfd, pathname);\n'
    '\tfilp = path_openat(&nd, op, flags | LOOKUP_RCU);',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tstruct filename *fake_pathname;\n'
    '#endif\n\n'
    '\tset_nameidata(&nd, dfd, pathname);\n'
    '\tfilp = path_openat(&nd, op, flags | LOOKUP_RCU);',
    'namei.c: do_filp_open fake_pathname var')

fix('fs/namei.c',
    '\t\tfilp = path_openat(&nd, op, flags | LOOKUP_REVAL);\n'
    '\trestore_nameidata();\n'
    '\treturn filp;\n'
    '}\n\n'
    'struct file *do_file_open_root(',
    '\t\tfilp = path_openat(&nd, op, flags | LOOKUP_REVAL);\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tif (!IS_ERR(filp) && unlikely(filp->f_inode->i_state & INODE_STATE_OPEN_REDIRECT) && current_uid().val < 2000) {\n'
    '\t\tfake_pathname = susfs_get_redirected_path(filp->f_inode->i_ino);\n'
    '\t\tif (!IS_ERR(fake_pathname)) {\n'
    '\t\t\trestore_nameidata();\n'
    '\t\t\tfilp_close(filp, NULL);\n'
    '\t\t\tset_nameidata(&nd, dfd, fake_pathname);\n'
    '\t\t\tfilp = path_openat(&nd, op, flags | LOOKUP_RCU);\n'
    '\t\t\tif (unlikely(filp == ERR_PTR(-ECHILD)))\n'
    '\t\t\t\tfilp = path_openat(&nd, op, flags);\n'
    '\t\t\tif (unlikely(filp == ERR_PTR(-ESTALE)))\n'
    '\t\t\t\tfilp = path_openat(&nd, op, flags | LOOKUP_REVAL);\n'
    '\t\t\trestore_nameidata();\n'
    '\t\t\tputname(fake_pathname);\n'
    '\t\t\treturn filp;\n'
    '\t\t}\n'
    '\t}\n'
    '#endif\n'
    '\trestore_nameidata();\n'
    '\treturn filp;\n'
    '}\n\n'
    'struct file *do_file_open_root(',
    'namei.c: do_filp_open open_redirect logic')

# ── fs/namespace.c ────────────────────────────────────────────────────────────
print("\n── fs/namespace.c ───────────────────────────────────────────────────")

# hunk #1 — includes and externs
fix('fs/namespace.c',
    '#include "pnode.h"\n'
    '#include "internal.h"\n\n'
    '/* Maximum number of mounts',
    '#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include "pnode.h"\n'
    '#include "internal.h"\n\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'extern bool susfs_is_current_ksu_domain(void);\n'
    'extern bool susfs_is_current_zygote_domain(void);\n\n'
    'static DEFINE_IDA(susfs_mnt_id_ida);\n'
    'static DEFINE_IDA(susfs_mnt_group_ida);\n'
    'static int susfs_mnt_id_start = DEFAULT_SUS_MNT_ID;\n'
    'static int susfs_mnt_group_start = DEFAULT_SUS_MNT_GROUP_ID;\n\n'
    '#define CL_ZYGOTE_COPY_MNT_NS BIT(24)\n'
    '#define CL_COPY_MNT_NS BIT(25)\n'
    '#endif\n\n'
    '#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT\n'
    'extern void susfs_auto_add_sus_ksu_default_mount(const char __user *to_pathname);\n'
    'bool susfs_is_auto_add_sus_ksu_default_mount_enabled = true;\n'
    '#endif\n'
    '#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT\n'
    'extern int susfs_auto_add_sus_bind_mount(const char *pathname, struct path *path_target);\n'
    'bool susfs_is_auto_add_sus_bind_mount_enabled = true;\n'
    '#endif\n'
    '#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT\n'
    'extern void susfs_auto_add_try_umount_for_bind_mount(struct path *path);\n'
    'bool susfs_is_auto_add_try_umount_for_bind_mount_enabled = true;\n'
    '#endif\n\n'
    '/* Maximum number of mounts',
    'namespace.c: susfs includes and externs')

# hunk #9 — clone_mnt alloc_vfsmnt
fix('fs/namespace.c',
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n'
    '\tif (!mnt)\n'
    '\t\treturn ERR_PTR(-ENOMEM);',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tbool is_current_ksu_domain = susfs_is_current_ksu_domain();\n'
    '\tbool is_current_zygote_domain = susfs_is_current_zygote_domain();\n\n'
    '\tif (unlikely(is_current_ksu_domain)) {\n'
    '\t\tif (!(flag & CL_COPY_MNT_NS)) {\n'
    '\t\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);\n'
    '\t\t\tgoto bypass_orig_flow;\n'
    '\t\t}\n'
    '\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, old->mnt_id);\n'
    '\t\tif (mnt) {\n'
    '\t\t\tmnt->mnt.susfs_mnt_id_backup = DEFAULT_SUS_MNT_ID_FOR_KSU_PROC_UNSHARE;\n'
    '\t\t}\n'
    '\t\tgoto bypass_orig_flow;\n'
    '\t}\n'
    '\tif (likely(is_current_zygote_domain) && (old->mnt_id >= DEFAULT_SUS_MNT_ID)) {\n'
    '\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);\n'
    '\t\tgoto bypass_orig_flow;\n'
    '\t}\n'
    '\tif ((flag & CL_COPY_MNT_NS) && (old->mnt_id >= DEFAULT_SUS_MNT_ID)) {\n'
    '\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);\n'
    '\t\tgoto bypass_orig_flow;\n'
    '\t}\n'
    '\tmnt = alloc_vfsmnt(old->mnt_devname, false, 0);\n'
    'bypass_orig_flow:\n'
    '#else\n'
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n'
    '#endif\n'
    '\tif (!mnt)\n'
    '\t\treturn ERR_PTR(-ENOMEM);',
    'namespace.c: clone_mnt SUSFS sus_mount alloc_vfsmnt')

# hunk #12 — do_mount (dput_out: is unique in file)
fix('fs/namespace.c',
    'dput_out:\n'
    '\tpath_put(&path);\n'
    '\treturn retval;\n'
    '}',
    '#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT\n'
    '\tif (!retval && susfs_is_auto_add_sus_ksu_default_mount_enabled &&\n'
    '\t\t\t(!(flags & (MS_REMOUNT | MS_BIND | MS_SHARED | MS_PRIVATE | MS_SLAVE | MS_UNBINDABLE)))) {\n'
    '\t\tif (susfs_is_current_ksu_domain()) {\n'
    '\t\t\tsusfs_auto_add_sus_ksu_default_mount(dir_name);\n'
    '\t\t}\n'
    '\t}\n'
    '#endif\n'
    'dput_out:\n'
    '\tpath_put(&path);\n'
    '\treturn retval;\n'
    '}',
    'namespace.c: do_mount auto_add_sus_ksu_default_mount')

# hunk #14 — copy_mnt_ns CL flags (RKP_NS_PROT wraps copy_tree)
fix('fs/namespace.c',
    '\tif (user_ns != ns->user_ns)\n'
    '\t\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\tnew = copy_tree(old, old->mnt->mnt_root, copy_flags);\n'
    '#else\n'
    '\tnew = copy_tree(old, old->mnt.mnt_root, copy_flags);',
    '\tif (user_ns != ns->user_ns)\n'
    '\t\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tcopy_flags |= CL_COPY_MNT_NS;\n'
    '\tif (is_zygote_pid) {\n'
    '\t\tcopy_flags |= CL_ZYGOTE_COPY_MNT_NS;\n'
    '\t}\n'
    '#endif\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\tnew = copy_tree(old, old->mnt->mnt_root, copy_flags);\n'
    '#else\n'
    '\tnew = copy_tree(old, old->mnt.mnt_root, copy_flags);',
    'namespace.c: copy_mnt_ns CL_COPY_MNT_NS flags')

# ── fs/notify/fdinfo.c ────────────────────────────────────────────────────────
print("\n── fs/notify/fdinfo.c ───────────────────────────────────────────────")
try:
    with open('fs/notify/fdinfo.c', 'r') as f:
        s = f.read()
    target = '//u32 mask = mark->mask & IN_ALL_EVENTS;'
    if target in s:
        with open('fs/notify/fdinfo.c', 'w') as f:
            f.write(s.replace(target, 'u32 mask = mark->mask & IN_ALL_EVENTS;', 1))
        print('✅ fdinfo.c: restored mask declaration')
    else:
        print('⚠️  fdinfo.c: //u32 pattern not found')
except FileNotFoundError:
    print('⚠️  fdinfo.c: not found')

# ── fs/proc/cmdline.c — SKIP ──────────────────────────────────────────────────
print("\n── fs/proc/cmdline.c — SKIP (Samsung custom impl) ───────────────────")

# ── fs/proc/task_mmu.c ────────────────────────────────────────────────────────
print("\n── fs/proc/task_mmu.c ───────────────────────────────────────────────")

fix('fs/proc/task_mmu.c',
    '#include <asm/elf.h>',
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include <asm/elf.h>',
    'task_mmu.c: add susfs_def.h include')

# ── fs/readdir.c ──────────────────────────────────────────────────────────────
print("\n── fs/readdir.c ─────────────────────────────────────────────────────")

fix_regex('fs/readdir.c',
    r'(int reclen = ALIGN\(offsetof\(struct linux_dirent, d_name\) \+ namlen \+ 2,\n\s+sizeof\(long\)\);\n\n)(\s+buf->error = -EINVAL;)',
    r'\1'
    r'#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    r'\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) && susfs_sus_ino_for_filldir64(ino)) {\n'
    r'\t\treturn 0;\n'
    r'\t}\n'
    r'#endif\n'
    r'\2',
    'readdir.c: filldir sus_path ino check')

fix_regex('fs/readdir.c',
    r'(int reclen = ALIGN\(offsetof\(struct linux_dirent64, d_name\) \+ namlen \+ 1,\n\s+sizeof\(u64\)\);\n\n)(\s+buf->error = -EINVAL;)',
    r'\1'
    r'#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    r'\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) && susfs_sus_ino_for_filldir64(ino)) {\n'
    r'\t\treturn 0;\n'
    r'\t}\n'
    r'#endif\n'
    r'\2',
    'readdir.c: filldir64 sus_path ino check')

# ── kernel/sys.c ──────────────────────────────────────────────────────────────
print("\n── kernel/sys.c ─────────────────────────────────────────────────────")

fix('kernel/sys.c',
    'SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n'
    '{\n'
    '\tint errno = 0;\n\n'
    '\tdown_read(&uts_sem);\n'
    '\tif (copy_to_user(name, utsname(), sizeof *name))\n'
    '\t\terrno = -EFAULT;\n'
    '\tup_read(&uts_sem);',
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    'extern void susfs_spoof_uname(struct new_utsname* tmp);\n'
    '#endif\n'
    'SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n'
    '{\n'
    '\tint errno = 0;\n'
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    '\tstruct new_utsname tmp;\n'
    '#endif\n\n'
    '\tdown_read(&uts_sem);\n'
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    '\tmemcpy(&tmp, utsname(), sizeof(tmp));\n'
    '\tsusfs_spoof_uname(&tmp);\n'
    '\tup_read(&uts_sem);\n'
    '\tif (copy_to_user(name, &tmp, sizeof(tmp)))\n'
    '\t\terrno = -EFAULT;\n'
    '#else\n'
    '\tif (copy_to_user(name, utsname(), sizeof *name))\n'
    '\t\terrno = -EFAULT;\n'
    '\tup_read(&uts_sem);\n'
    '#endif',
    'sys.c: susfs_spoof_uname in newuname')

# ── include/linux/susfs_def.h ─────────────────────────────────────────────────
print("\n── include/linux/susfs_def.h ────────────────────────────────────────")

# susfs_def.h — linux/bits.h added in 4.6, not present in 4.4
fix('include/linux/susfs_def.h',
    '#include <linux/bits.h>',
    '#include <linux/bitops.h>',
    'susfs_def.h: bits.h → bitops.h (not in 4.4)')

print("\n✅ susfs_hunk_fix_note8.py complete")
