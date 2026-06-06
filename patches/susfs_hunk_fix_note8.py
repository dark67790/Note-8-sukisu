#!/usr/bin/env python3
# susfs_hunk_fix_note8.py — SUSFS kernel-4.9 → Samsung 4.4 compat fixes
# Run from kernel_source/ after 50_add_susfs_in_kernel-4.9.patch applied
#
# Failure root causes per file:
#   dcache.c    — Samsung 4.4 __d_lookup_rcu has different loop structure
#   namei.c     — 11 hunks: may_create_in_sticky absent, HAS_UNMAPPED_ID
#                 absent, may_o_create non-const, lookup_open restructured,
#                 do_filp_open context before function differs
#   namespace.c — RKP_NS_PROT ifdefs block anchor lines; Samsung extras
#   cmdline.c   — Samsung uses updated_command_line, completely different
#   task_mmu.c  — sched/mm.h replaces mm_inline.h as last include
#   readdir.c   — verify_dirent_name absent in 4.4; buf->error = -EINVAL instead
#   sys.c       — newuname uses copy_to_user directly, no memcpy+spoof pattern

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

# ─────────────────────────────────────────────────────────────────────────────
# fs/dcache.c — hunk #2
# Samsung 4.4 __d_lookup_rcu returns found dentry with *seqp=seq before NULL
# SUSFS check goes just before that return point so sus_path dentrys continue
# ─────────────────────────────────────────────────────────────────────────────
print("── fs/dcache.c ──────────────────────────────────────────────────────")

fix('fs/dcache.c',
    '\t\t*seqp = seq;\n\t\treturn dentry;\n\t}\n\treturn NULL;\n}',
    '\t\t\t/* susfs: hide sus_path from non-root user app processes */\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\t\tif (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\t\t\tcontinue;\n'
    '\t\t\t}\n'
    '#endif\n'
    '\t\t*seqp = seq;\n'
    '\t\treturn dentry;\n'
    '\t}\n'
    '\treturn NULL;\n'
    '}',
    'dcache.c: __d_lookup_rcu sus_path check')

# ─────────────────────────────────────────────────────────────────────────────
# fs/namei.c — 11 hunks
# hunk #4  SKIP: may_create_in_sticky doesn't exist in Samsung 4.4
# hunk #8  filename_lookup: restore_nameidata+putname anchor
# hunk #9  may_delete: IS_APPEND+check_sticky anchor (no HAS_UNMAPPED_ID in 4.4)
# hunk #10 may_create: audit_inode_child anchor
# hunk #11 may_open: !inode + switch anchor
# hunk #12 may_o_create: wraps security_path_mknod (no const on struct path)
# hunk #13 lookup_open: cached positive dentry single-line goto
# hunk #14 lookup_open: skip (atomic_open is direct return in Samsung 4.4)
# hunk #15 lookup_open: after lookup_real IS_ERR check
# hunk #16 do_filp_open: extern + fake_pathname var
# hunk #17 do_filp_open: open_redirect logic before restore_nameidata
# ─────────────────────────────────────────────────────────────────────────────
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

# hunk #9 — may_delete
# Samsung 4.4 lacks HAS_UNMAPPED_ID — that's why patch context didn't match
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

# hunk #10 — may_create
fix('fs/namei.c',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '\tstruct user_namespace *s_user_ns;\n'
    '\taudit_inode_child(dir, child, AUDIT_TYPE_CHILD_CREATE);',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tint error;\n'
    '#endif\n'
    '\tstruct user_namespace *s_user_ns;\n'
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

# hunk #12 — may_o_create
# Samsung 4.4: non-const struct path*, starts directly with int error = security_path_mknod
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
# Samsung 4.4 uses single-line `if (!need_lookup && dentry->d_inode) goto out_no_open;`
# 4.9 used `if (dentry->d_inode) { ... goto out_no_open; }` (different test)
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

# hunk #14 — SKIP
# Samsung 4.4 lookup_open does `return atomic_open(...)` directly
# Cannot intercept return value without restructuring; not critical

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

# hunks #16 + #17 — do_filp_open open_redirect
# Samsung 4.4 do_filp_open body matches 4.9 exactly — fails only because
# the context BEFORE the function (end of path_openat) differs
fix('fs/namei.c',
    'struct file *do_filp_open(int dfd, struct filename *pathname,\n'
    '\t\t\tconst struct open_flags *op)\n'
    '{\n'
    '\tstruct nameidata nd;\n'
    '\tint flags = op->lookup_flags;\n'
    '\tstruct file *filp;\n'
    '\n'
    '\tset_nameidata(&nd, dfd, pathname);',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern struct filename* susfs_get_redirected_path(unsigned long ino);\n'
    '#endif\n'
    '\n'
    'struct file *do_filp_open(int dfd, struct filename *pathname,\n'
    '\t\t\tconst struct open_flags *op)\n'
    '{\n'
    '\tstruct nameidata nd;\n'
    '\tint flags = op->lookup_flags;\n'
    '\tstruct file *filp;\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tstruct filename *fake_pathname;\n'
    '#endif\n'
    '\n'
    '\tset_nameidata(&nd, dfd, pathname);',
    'namei.c: do_filp_open open_redirect extern + var')

fix('fs/namei.c',
    '\t\tfilp = path_openat(&nd, op, flags | LOOKUP_REVAL);\n'
    '\trestore_nameidata();\n'
    '\treturn filp;\n'
    '}\n'
    '\n'
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
    '}\n'
    '\n'
    'struct file *do_file_open_root(',
    'namei.c: do_filp_open open_redirect logic')

# ─────────────────────────────────────────────────────────────────────────────
# fs/namespace.c — 4 hunks
# hunk #1  includes/externs: Samsung adds slub_def.h + fslog.h between
#          task_work.h and pnode.h — anchor on pnode.h
# hunk #9  clone_mnt: RKP_NS_PROT ifdefs broke context; alloc_vfsmnt call
#          must be replaced with SUSFS conditional (alloc_vfsmnt now 3-arg)
# hunk #12 do_mount: insert before dput_out label
# hunk #14 copy_mnt_ns: RKP_NS_PROT ifdef around copy_tree broke context
# ─────────────────────────────────────────────────────────────────────────────
print("\n── fs/namespace.c ───────────────────────────────────────────────────")

# hunk #1 — includes and externs
fix('fs/namespace.c',
    '#include "pnode.h"\n'
    '#include "internal.h"\n'
    '\n'
    '/* Maximum number of mounts',
    '#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include "pnode.h"\n'
    '#include "internal.h"\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'extern bool susfs_is_current_ksu_domain(void);\n'
    'extern bool susfs_is_current_zygote_domain(void);\n'
    '\n'
    'static DEFINE_IDA(susfs_mnt_id_ida);\n'
    'static DEFINE_IDA(susfs_mnt_group_ida);\n'
    'static int susfs_mnt_id_start = DEFAULT_SUS_MNT_ID;\n'
    'static int susfs_mnt_group_start = DEFAULT_SUS_MNT_GROUP_ID;\n'
    '\n'
    '#define CL_ZYGOTE_COPY_MNT_NS BIT(24)\n'
    '#define CL_COPY_MNT_NS BIT(25)\n'
    '#endif\n'
    '\n'
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
    '#endif\n'
    '\n'
    '/* Maximum number of mounts',
    'namespace.c: susfs includes and externs after pnode.h')

# hunk #9 — clone_mnt alloc_vfsmnt replacement
# After succeeding hunks alloc_vfsmnt now takes (name, bool, int)
# The single remaining 1-arg call is inside clone_mnt due to context mismatch
fix('fs/namespace.c',
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n'
    '\tif (!mnt)\n'
    '\t\treturn ERR_PTR(-ENOMEM);',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tbool is_current_ksu_domain = susfs_is_current_ksu_domain();\n'
    '\tbool is_current_zygote_domain = susfs_is_current_zygote_domain();\n'
    '\n'
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

# hunk #12 — do_mount auto_add_sus_ksu_default_mount before dput_out
fix('fs/namespace.c',
    'dput_out:\n'
    '\tpath_put(&path);\n'
    '\treturn retval;\n'
    '}\n'
    '\nstatic int',
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
    '}\n'
    '\nstatic int',
    'namespace.c: do_mount auto_add_sus_ksu_default_mount')

# hunk #14 — copy_mnt_ns CL_COPY_MNT_NS flag
# Samsung 4.4 wraps copy_tree with RKP_NS_PROT — anchor on both branches
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

# ─────────────────────────────────────────────────────────────────────────────
# fs/proc/cmdline.c — SKIP
# Samsung 4.4 has completely custom cmdline.c using updated_command_line
# and proc_cmdline_set() — incompatible with SUSFS SPOOF_CMDLINE hook.
# Samsung already strips debug_level/odin_download/warranty_bit/verifiedbootstate.
# Set CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=n in defconfig.
# ─────────────────────────────────────────────────────────────────────────────
print("\n── fs/proc/cmdline.c — SKIP (Samsung custom impl, already spoofs) ───")

# ─────────────────────────────────────────────────────────────────────────────
# fs/proc/task_mmu.c — hunk #1
# Samsung 4.4 has sched/mm.h (Samsung backport) instead of mm_inline.h
# as last include before asm/elf.h — anchor on asm/elf.h instead
# ─────────────────────────────────────────────────────────────────────────────
print("\n── fs/proc/task_mmu.c ───────────────────────────────────────────────")

fix('fs/proc/task_mmu.c',
    '#include <asm/elf.h>',
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include <asm/elf.h>',
    'task_mmu.c: add susfs_def.h include')

# ─────────────────────────────────────────────────────────────────────────────
# fs/readdir.c — hunks #2 and #3
# Samsung 4.4 lacks verify_dirent_name() — patch anchored on it, failed.
# Actual code: buf->error = -EINVAL; Use that as anchor instead.
# ─────────────────────────────────────────────────────────────────────────────
print("\n── fs/readdir.c ─────────────────────────────────────────────────────")

# hunk #2 — filldir (linux_dirent, 32-bit)
fix('fs/readdir.c',
    '\tint reclen = ALIGN(offsetof(struct linux_dirent, d_name) + namlen + 2,\n'
    '\t\t\tsizeof(long));\n'
    '\n'
    '\tbuf->error = -EINVAL;',
    '\tint reclen = ALIGN(offsetof(struct linux_dirent, d_name) + namlen + 2,\n'
    '\t\t\tsizeof(long));\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) && susfs_sus_ino_for_filldir64(ino)) {\n'
    '\t\treturn 0;\n'
    '\t}\n'
    '#endif\n'
    '\tbuf->error = -EINVAL;',
    'readdir.c: filldir sus_path ino check')

# hunk #3 — filldir64 (linux_dirent64, 64-bit)
fix('fs/readdir.c',
    '\tint reclen = ALIGN(offsetof(struct linux_dirent64, d_name) + namlen + 1,\n'
    '\t\t\tsizeof(u64));\n'
    '\n'
    '\tbuf->error = -EINVAL;',
    '\tint reclen = ALIGN(offsetof(struct linux_dirent64, d_name) + namlen + 1,\n'
    '\t\t\tsizeof(u64));\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) && susfs_sus_ino_for_filldir64(ino)) {\n'
    '\t\treturn 0;\n'
    '\t}\n'
    '#endif\n'
    '\tbuf->error = -EINVAL;',
    'readdir.c: filldir64 sus_path ino check')

# ─────────────────────────────────────────────────────────────────────────────
# kernel/sys.c — hunk #1
# Samsung 4.4 newuname does copy_to_user directly without memcpy+tmp pattern.
# Restructure to use tmp buffer so susfs_spoof_uname can modify before copy.
# ─────────────────────────────────────────────────────────────────────────────
print("\n── kernel/sys.c ─────────────────────────────────────────────────────")

fix('kernel/sys.c',
    'SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n'
    '{\n'
    '\tint errno = 0;\n'
    '\n'
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
    '#endif\n'
    '\n'
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

print("\n✅ susfs_hunk_fix_note8.py complete")