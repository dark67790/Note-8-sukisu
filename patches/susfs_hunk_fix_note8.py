#!/usr/bin/env python3
# susfs_hunk_fix_note8.py — SUSFS kernel-4.9 → Samsung 4.4 (dreamlte / SM-N950F)
# Run from kernel_source/ after:
#   patch -p1 --fuzz=0 --reject-file=$TMPDIR/susfs.rej < 50_add_susfs_in_kernel-4.9.patch
# Handles every rejected/incompatible hunk for Samsung's 4.4 source tree.

import re, os

def fix(path, old, new, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found — SKIP")
        return
    if old not in s:
        print(f"⚠️  {label}: anchor not found — already applied or source mismatch")
        return
    if new in s:
        print(f"↩️  {label}: already applied — SKIP")
        return
    with open(path, 'w') as f:
        f.write(s.replace(old, new, 1))
    print(f"✅ {label}")

def fix_regex(path, pattern, replacement, label):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found — SKIP")
        return
    if not re.search(pattern, s, re.DOTALL):
        print(f"⚠️  {label}: pattern not found — already applied or source mismatch")
        return
    result = re.sub(pattern, replacement, s, count=1, flags=re.DOTALL)
    if result == s:
        print(f"↩️  {label}: already applied — SKIP")
        return
    with open(path, 'w') as f:
        f.write(result)
    print(f"✅ {label}")

# ── include/linux/susfs_def.h ─────────────────────────────────────────────────
print("── include/linux/susfs_def.h ────────────────────────────────────────")

fix('include/linux/susfs_def.h',
    '#include <linux/bits.h>',
    '#include <linux/bitops.h>',
    'susfs_def.h: bits.h → bitops.h (bits.h not in 4.4)')

# ── include/linux/mount.h ─────────────────────────────────────────────────────
print("\n── include/linux/mount.h ────────────────────────────────────────────")

# FAILED: add susfs_mnt_id_backup to vfsmount struct
# Samsung struct ends: int mnt_flags; void *data; };
fix('include/linux/mount.h',
    '\tint mnt_flags;\n'
    '\tvoid *data;\n'
    '};',
    '\tint mnt_flags;\n'
    '\tvoid *data;\n'
    '#ifdef CONFIG_KSU_SUSFS\n'
    '\tu64 susfs_mnt_id_backup;\n'
    '#endif\n'
    '};',
    'mount.h: add susfs_mnt_id_backup to vfsmount')

# ── include/linux/sched.h ─────────────────────────────────────────────────────
print("\n── include/linux/sched.h ────────────────────────────────────────────")

# FAILED at 2204 — Samsung has thread_struct at 2014, no stack_refcount guard
fix('include/linux/sched.h',
    '/* CPU-specific state of this task */\n'
    '\tstruct thread_struct thread;',
    '/* CPU-specific state of this task */\n'
    '#ifdef CONFIG_KSU_SUSFS\n'
    '\tu64 susfs_task_state;\n'
    '\tu64 susfs_last_fake_mnt_id;\n'
    '#endif\n'
    '\tstruct thread_struct thread;',
    'sched.h: add susfs fields to task_struct (Samsung 4.4 line 2014)')

# ── fs/dcache.c ───────────────────────────────────────────────────────────────
print("\n── fs/dcache.c ──────────────────────────────────────────────────────")

# FAILED hunk #2 at 2221.
# Upstream 4.9: if (dentry_cmp() != 0) continue  — skip non-match, fall through on match
# Samsung 4.4:  if (!dentry_cmp())  return dentry — inverted, single-line direct return
# Expand the single-line if into a block to inject the sus_path check.
fix('fs/dcache.c',
    '\t\tif (!dentry_cmp(dentry, str, hashlen_len(hashlen)))\n'
    '\t\t\treturn dentry;\n'
    '\t}\n'
    '\treturn NULL;\n'
    '}',
    '\t\tif (!dentry_cmp(dentry, str, hashlen_len(hashlen))) {\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\t\tif (dentry->d_inode &&\n'
    '\t\t\t    unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) &&\n'
    '\t\t\t    likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC))\n'
    '\t\t\t\tcontinue;\n'
    '#endif\n'
    '\t\t\treturn dentry;\n'
    '\t\t}\n'
    '\t}\n'
    '\treturn NULL;\n'
    '}',
    'dcache.c: hunk#2 — __d_lookup_rcu sus_path (Samsung inverted !dentry_cmp)')

# ── fs/namei.c ────────────────────────────────────────────────────────────────
print("\n── fs/namei.c ───────────────────────────────────────────────────────")

# hunk #1 FAILED at 38: add susfs_def.h include
# Samsung includes end: asm/uaccess.h → blank → "internal.h" "mount.h"
fix('fs/namei.c',
    '#include <asm/uaccess.h>\n'
    '\n'
    '#include "internal.h"',
    '#include <asm/uaccess.h>\n'
    '#if defined(CONFIG_KSU_SUSFS_SUS_PATH) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '\n'
    '#include "internal.h"',
    'namei.c: hunk#1 — susfs_def.h include')

# hunk #4 FAILED at 1058: may_create_in_sticky — function does not exist in Samsung 4.4
print("↩️  namei.c: hunk#4 — may_create_in_sticky absent in Samsung 4.4 — SKIP")

# hunk #6 FAILED at 1732: lookup_slow sus_path check
# 4.9: inode_lock_shared / inode_unlock_shared, has out: label
# Samsung 4.4: mutex_lock / mutex_unlock, no out: label, returns via follow_managed()
fix('fs/namei.c',
    '\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\tif (IS_ERR(dentry))\n'
    '\t\treturn PTR_ERR(dentry);\n'
    '\tpath->mnt = nd->path.mnt;\n'
    '\tpath->dentry = dentry;\n'
    '\treturn follow_managed(path, nd);\n'
    '}',
    '\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\tif (IS_ERR(dentry))\n'
    '\t\treturn PTR_ERR(dentry);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (dentry->d_inode &&\n'
    '\t    unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) &&\n'
    '\t    likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\tdput(dentry);\n'
    '\t\treturn ERR_PTR(-ENOENT);\n'
    '\t}\n'
    '#endif\n'
    '\tpath->mnt = nd->path.mnt;\n'
    '\tpath->dentry = dentry;\n'
    '\treturn follow_managed(path, nd);\n'
    '}',
    'namei.c: hunk#6 — lookup_slow sus_path (Samsung mutex variant, no out: label)')

# hunks #7,8,11,16,17 SUCCEEDED — no action needed

# hunk #9 FAILED at 2877: may_delete — Samsung 4.4 has no HAS_UNMAPPED_ID
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
    '\tif (unlikely(inode->i_state & INODE_STATE_SUS_PATH) &&\n'
    '\t    likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC))\n'
    '\t\treturn -ENOENT;\n'
    '#endif\n'
    '\n'
    '\tif (check_sticky(dir, inode) || IS_APPEND(inode) ||\n'
    '\t    IS_IMMUTABLE(inode) || IS_SWAPFILE(inode))\n'
    '\t\treturn -EPERM;',
    'namei.c: hunk#9 — may_delete sus_path (no HAS_UNMAPPED_ID in Samsung 4.4)')

# hunk #10 FAILED at 2905: may_create — Samsung 4.4 has no s_user_ns member
fix('fs/namei.c',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '\taudit_inode_child(dir, child, AUDIT_TYPE_CHILD_CREATE);\n'
    '\tif (child->d_inode)\n'
    '\t\treturn -EEXIST;',
    'static inline int may_create(struct vfsmount *mnt, struct inode *dir, struct dentry *child)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tint error;\n'
    '#endif\n'
    '\taudit_inode_child(dir, child, AUDIT_TYPE_CHILD_CREATE);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (child->d_inode &&\n'
    '\t    unlikely(child->d_inode->i_state & INODE_STATE_SUS_PATH) &&\n'
    '\t    likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\terror = inode_permission2(mnt, dir, MAY_WRITE | MAY_EXEC);\n'
    '\t\tif (error)\n'
    '\t\t\treturn error;\n'
    '\t\treturn -ENOENT;\n'
    '\t}\n'
    '#endif\n'
    '\tif (child->d_inode)\n'
    '\t\treturn -EEXIST;',
    'namei.c: hunk#10 — may_create sus_path (no s_user_ns in Samsung 4.4)')

# hunk #12 FAILED at 3088: may_o_create — Samsung uses non-const struct path*, no s_user_ns
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
    '\tif (dentry->d_inode &&\n'
    '\t    unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) &&\n'
    '\t    likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC)) {\n'
    '\t\terror = inode_permission2(dir->mnt, dir->dentry->d_inode, MAY_WRITE | MAY_EXEC);\n'
    '\t\tif (error)\n'
    '\t\t\treturn error;\n'
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
    'namei.c: hunk#12 — may_o_create sus_path (non-const path, no s_user_ns in Samsung 4.4)')

# hunks #13,14,15 FAILED: lookup_open paths
# Samsung 4.4 lookup_open starts with BUG_ON(dentry->d_inode) — only handles negative dentries.
# No equivalent location for cached-positive / atomic_open / lookup_real sus_path checks.
# hunk#11 (may_open) SUCCEEDED at offset -241 and provides the primary open-time protection.
print("↩️  namei.c: hunks#13,14,15 — lookup_open incompatible with Samsung 4.4 structure — SKIP")
print("           (hunk#11 may_open already applied — equivalent protection)")

# ── fs/namespace.c ────────────────────────────────────────────────────────────
print("\n── fs/namespace.c ───────────────────────────────────────────────────")

# hunk #1 FAILED at 25: includes + externs
# Samsung has extra #include <linux/slub_def.h> and #include <linux/fslog.h>
# between task_work.h and "pnode.h" — anchor on fslog.h line.
fix('fs/namespace.c',
    '#include <linux/fslog.h>\n'
    '#include "pnode.h"\n'
    '#include "internal.h"',
    '#include <linux/fslog.h>\n'
    '#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include "pnode.h"\n'
    '#include "internal.h"\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'extern bool susfs_is_current_ksu_domain(void);\n'
    'extern bool susfs_is_current_zygote_domain(void);\n'
    'extern int susfs_mnt_alloc_id(struct mount *mnt);\n'
    '\n'
    'static DEFINE_IDA(susfs_mnt_id_ida);\n'
    'static DEFINE_IDA(susfs_mnt_group_ida);\n'
    'static int susfs_mnt_id_start = DEFAULT_SUS_MNT_ID;\n'
    'static int susfs_mnt_group_start = DEFAULT_SUS_MNT_GROUP_ID;\n'
    '\n'
    '#define CL_ZYGOTE_COPY_MNT_NS BIT(24)\n'
    '#define CL_COPY_MNT_NS        BIT(25)\n'
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
    '#endif',
    'namespace.c: hunk#1 — susfs includes + externs (Samsung fslog.h anchor)')

# hunk #6 FAILED at 274: alloc_vfsmnt signature
# CRITICAL: hunk#7 (vfs_kern_mount) already SUCCEEDED and added 3-arg calls inside
# #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT blocks. The 1-arg definition must gain a conditional
# 3-arg variant so the SUS_MOUNT path compiles.
fix('fs/namespace.c',
    'static struct mount *alloc_vfsmnt(const char *name)\n'
    '{\n'
    '\tstruct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);\n'
    '\tif (mnt) {\n'
    '\t\tint err;\n'
    '\n'
    '\t\terr = mnt_alloc_id(mnt);\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out_free_cache;\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\t\terr = mnt_alloc_vfsmount(mnt);\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out_free_cache;\n'
    '#endif',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'static struct mount *alloc_vfsmnt(const char *name, bool should_spoof, int custom_mnt_id)\n'
    '#else\n'
    'static struct mount *alloc_vfsmnt(const char *name)\n'
    '#endif\n'
    '{\n'
    '\tstruct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);\n'
    '\tif (mnt) {\n'
    '\t\tint err;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\t\tif (should_spoof) {\n'
    '\t\t\tif (!custom_mnt_id) {\n'
    '\t\t\t\terr = susfs_mnt_alloc_id(mnt);\n'
    '\t\t\t} else {\n'
    '\t\t\t\tmnt->mnt_id = custom_mnt_id;\n'
    '\t\t\t\terr = 0;\n'
    '\t\t\t}\n'
    '\t\t\tgoto bypass_orig_flow;\n'
    '\t\t}\n'
    '#endif\n'
    '\t\terr = mnt_alloc_id(mnt);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'bypass_orig_flow:\n'
    '#endif\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out_free_cache;\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\t\terr = mnt_alloc_vfsmount(mnt);\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out_free_cache;\n'
    '#endif',
    'namespace.c: hunk#6 — alloc_vfsmnt conditional 3-arg signature + spoof logic')

# hunk #8 FAILED at 1091: vfs_kern_mount zygote mnt_id reorder — SKIP
# hunk#7 already patched the KSU alloc path; hunk#8 adds zygote reorder after mnt_parent=mnt.
# Samsung uses RKP_NS_PROT so mnt->mnt.X is actually mnt->mnt->X — skip to avoid ptr mismatch.
print("↩️  namespace.c: hunk#8 — vfs_kern_mount zygote reorder skipped (RKP_NS_PROT ptr mismatch)")

# hunk #9 FAILED at 1119: clone_mnt — KSU/zygote domain logic before alloc_vfsmnt
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
    '\t\tif (mnt)\n'
    '\t\t\tmnt->mnt.susfs_mnt_id_backup = DEFAULT_SUS_MNT_ID_FOR_KSU_PROC_UNSHARE;\n'
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
    'namespace.c: hunk#9 — clone_mnt KSU/zygote alloc_vfsmnt logic')

# hunk #10 FAILED at 1172: clone_mnt — zygote mnt_id reorder after mnt_parent=mnt
# Same RKP_NS_PROT issue as hunk#8 — skip to avoid pointer mismatch.
print("↩️  namespace.c: hunk#10 — clone_mnt zygote reorder skipped (RKP_NS_PROT ptr mismatch)")

# hunk #12 FAILED at 3027: do_mount — AUTO_ADD before dput_out:
# dput_out: is unique in the file (line 3422 in Samsung) — safe anchor.
fix('fs/namespace.c',
    'dput_out:\n'
    '\tpath_put(&path);\n'
    '\treturn retval;\n'
    '}',
    '#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT\n'
    '\tif (!retval && susfs_is_auto_add_sus_ksu_default_mount_enabled &&\n'
    '\t    !(flags & (MS_REMOUNT | MS_BIND | MS_SHARED |\n'
    '\t               MS_PRIVATE | MS_SLAVE | MS_UNBINDABLE))) {\n'
    '\t\tif (susfs_is_current_ksu_domain())\n'
    '\t\t\tsusfs_auto_add_sus_ksu_default_mount(dir_name);\n'
    '\t}\n'
    '#endif\n'
    'dput_out:\n'
    '\tpath_put(&path);\n'
    '\treturn retval;\n'
    '}',
    'namespace.c: hunk#12 — do_mount AUTO_ADD before dput_out')

# hunk #14 FAILED at 3127: copy_mnt_ns — CL_COPY_MNT_NS flags
# hunk#13 SUCCEEDED (is_zygote_pid declared at line 3479).
# Samsung uses RKP_NS_PROT variant for copy_tree (mnt->mnt_root not mnt.mnt_root).
fix('fs/namespace.c',
    '\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\tnew = copy_tree(old, old->mnt->mnt_root, copy_flags);',
    '\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tcopy_flags |= CL_COPY_MNT_NS;\n'
    '\tif (is_zygote_pid)\n'
    '\t\tcopy_flags |= CL_ZYGOTE_COPY_MNT_NS;\n'
    '#endif\n'
    '#ifdef CONFIG_RKP_NS_PROT\n'
    '\tnew = copy_tree(old, old->mnt->mnt_root, copy_flags);',
    'namespace.c: hunk#14 — copy_mnt_ns CL_COPY_MNT_NS flags (RKP_NS_PROT anchor)')

# hunk #15 FAILED at 3163: copy_mnt_ns — zygote mnt_id reassignment loop
# Confirmed anchor: Samsung RKP variant ends while loop with
#   p = next_mnt(p, old);  }  namespace_unlock();
# hunk#13 already declared is_zygote_pid and last_entry_mnt_id (succeeded at +371).
fix('fs/namespace.c',
    '\t\tp = next_mnt(p, old);\n'
    '\t}\n'
    '\tnamespace_unlock();',
    '\t\tp = next_mnt(p, old);\n'
    '\t}\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (is_zygote_pid) {\n'
    '\t\tlast_entry_mnt_id = list_first_entry(&new_ns->list, struct mount, mnt_list)->mnt_id;\n'
    '\t\tlist_for_each_entry(q, &new_ns->list, mnt_list) {\n'
    '\t\t\tif (unlikely(q->mnt_id >= DEFAULT_SUS_MNT_ID))\n'
    '\t\t\t\tcontinue;\n'
    '\t\t\tq->mnt.susfs_mnt_id_backup = q->mnt_id;\n'
    '\t\t\tq->mnt_id = last_entry_mnt_id++;\n'
    '\t\t}\n'
    '\t}\n'
    '\tcurrent->susfs_last_fake_mnt_id = last_entry_mnt_id;\n'
    '#endif\n'
    '\tnamespace_unlock();',
    'namespace.c: hunk#15 — copy_mnt_ns zygote mnt_id reassignment loop')

# hunk #16 FAILED at 3703: EOF additions — susfs_run_try_umount + susfs_is_mnt_devname_ksu
# Samsung file ends cleanly at mntns_operations = {...};
fix('fs/namespace.c',
    'const struct proc_ns_operations mntns_operations = {\n'
    '\t.name\t\t= "mnt",\n'
    '\t.type\t\t= CLONE_NEWNS,\n'
    '\t.get\t\t= mntns_get,\n'
    '\t.put\t\t= mntns_put,\n'
    '\t.install\t= mntns_install,\n'
    '};',
    'const struct proc_ns_operations mntns_operations = {\n'
    '\t.name\t\t= "mnt",\n'
    '\t.type\t\t= CLONE_NEWNS,\n'
    '\t.get\t\t= mntns_get,\n'
    '\t.put\t\t= mntns_put,\n'
    '\t.install\t= mntns_install,\n'
    '};\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT\n'
    'extern void susfs_try_umount_all(uid_t uid);\n'
    'void susfs_run_try_umount_for_current_mnt_ns(void)\n'
    '{\n'
    '\tstruct mount *mnt;\n'
    '\tstruct mnt_namespace *mnt_ns;\n'
    '\n'
    '\tmnt_ns = current->nsproxy->mnt_ns;\n'
    '\tnamespace_lock();\n'
    '\tlist_for_each_entry(mnt, &mnt_ns->list, mnt_list) {\n'
    '\t\tif (mnt->mnt_id >= DEFAULT_SUS_MNT_ID)\n'
    '\t\t\tchange_mnt_propagation(mnt, MS_PRIVATE);\n'
    '\t}\n'
    '\tnamespace_unlock();\n'
    '\tsusfs_try_umount_all(current_uid().val);\n'
    '}\n'
    '#endif\n'
    '#ifdef CONFIG_KSU_SUSFS\n'
    'bool susfs_is_mnt_devname_ksu(struct path *path)\n'
    '{\n'
    '\tstruct mount *mnt;\n'
    '\n'
    '\tif (path && path->mnt) {\n'
    '\t\tmnt = real_mount(path->mnt);\n'
    '\t\tif (mnt && mnt->mnt_devname && !strcmp(mnt->mnt_devname, "KSU"))\n'
    '\t\t\treturn true;\n'
    '\t}\n'
    '\treturn false;\n'
    '}\n'
    '#endif',
    'namespace.c: hunk#16 — EOF add susfs_run_try_umount + susfs_is_mnt_devname_ksu')

# ── fs/proc_namespace.c ───────────────────────────────────────────────────────
print("\n── fs/proc_namespace.c ──────────────────────────────────────────────")

# show_vfsmnt: inject before first show_devname test (unique: has mangle() in else branch)
fix('fs/proc_namespace.c',
    '\tstruct super_block *sb = mnt_path.dentry->d_sb;\n'
    '\n'
    '\tif (sb->s_op->show_devname) {\n'
    '\t\terr = sb->s_op->show_devname(m, mnt_path.dentry);\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out;\n'
    '\t} else {\n'
    '\t\tmangle(m, r->mnt_devname ? r->mnt_devname : "none");\n'
    '\t}',
    '\tstruct super_block *sb = mnt_path.dentry->d_sb;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (unlikely(r->mnt_id >= DEFAULT_SUS_MNT_ID))\n'
    '\t\treturn 0;\n'
    '#endif\n'
    '\n'
    '\tif (sb->s_op->show_devname) {\n'
    '\t\terr = sb->s_op->show_devname(m, mnt_path.dentry);\n'
    '\t\tif (err)\n'
    '\t\t\tgoto out;\n'
    '\t} else {\n'
    '\t\tmangle(m, r->mnt_devname ? r->mnt_devname : "none");\n'
    '\t}',
    'proc_namespace.c: show_vfsmnt sus_mount mnt_id filter')

# show_mountinfo: inject before seq_printf with r->mnt_id (unique to this function)
fix('fs/proc_namespace.c',
    '\tseq_printf(m, "%i %i %u:%u ", r->mnt_id, r->mnt_parent->mnt_id,\n'
    '\t\t   MAJOR(sb->s_dev), MINOR(sb->s_dev));',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (unlikely(r->mnt_id >= DEFAULT_SUS_MNT_ID))\n'
    '\t\treturn 0;\n'
    '#endif\n'
    '\tseq_printf(m, "%i %i %u:%u ", r->mnt_id, r->mnt_parent->mnt_id,\n'
    '\t\t   MAJOR(sb->s_dev), MINOR(sb->s_dev));',
    'proc_namespace.c: show_mountinfo sus_mount mnt_id filter')

# show_vfsstat: inject before /* device */ comment (unique to this function)
fix('fs/proc_namespace.c',
    '\tint err = 0;\n'
    '\n'
    '\t/* device */\n'
    '\tif (sb->s_op->show_devname) {',
    '\tint err = 0;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (unlikely(r->mnt_id >= DEFAULT_SUS_MNT_ID))\n'
    '\t\treturn 0;\n'
    '#endif\n'
    '\n'
    '\t/* device */\n'
    '\tif (sb->s_op->show_devname) {',
    'proc_namespace.c: show_vfsstat sus_mount mnt_id filter')

# ── fs/proc/task_mmu.c ────────────────────────────────────────────────────────
print("\n── fs/proc/task_mmu.c ───────────────────────────────────────────────")

# hunk #1 FAILED at 16: add susfs_def.h include
# Upstream context: #include <linux/mm_inline.h> — Samsung has #include <linux/sched/mm.h>
fix('fs/proc/task_mmu.c',
    '#include <linux/sched/mm.h>\n'
    '\n'
    '#include <asm/elf.h>',
    '#include <linux/sched/mm.h>\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '\n'
    '#include <asm/elf.h>',
    'task_mmu.c: hunk#1 — susfs_def.h include (Samsung uses sched/mm.h)')

# hunk #2 FAILED at 346: extern before show_map_vma
# hunk #3 SUCCEEDED — the call inside show_map_vma is already there (confirmed line 385)
fix('fs/proc/task_mmu.c',
    'show_map_vma(struct seq_file *m, struct vm_area_struct *vma, int is_pid)\n'
    '{',
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    'extern void susfs_sus_ino_for_show_map_vma(unsigned long ino, dev_t *out_dev, unsigned long *out_ino);\n'
    '#endif\n'
    'show_map_vma(struct seq_file *m, struct vm_area_struct *vma, int is_pid)\n'
    '{',
    'task_mmu.c: hunk#2 — susfs_sus_ino_for_show_map_vma extern before show_map_vma')

# ── fs/readdir.c ──────────────────────────────────────────────────────────────
print("\n── fs/readdir.c ─────────────────────────────────────────────────────")
# hunk #1 SUCCEEDED (extern at line 28 already present)
# hunks #2,3 FAILED: actual ino checks in filldir / filldir64

fix_regex('fs/readdir.c',
    r'(int reclen = ALIGN\(offsetof\(struct linux_dirent, d_name\) \+ namlen \+ 2,\n'
    r'\s+sizeof\(long\)\);\n\n)(\s+buf->error = -EINVAL)',
    r'\1'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) &&\n'
    '\t    susfs_sus_ino_for_filldir64(ino)) {\n'
    '\t\treturn 0;\n'
    '\t}\n'
    '#endif\n'
    r'\2',
    'readdir.c: hunk#2 — filldir sus_path ino check')

fix_regex('fs/readdir.c',
    r'(int reclen = ALIGN\(offsetof\(struct linux_dirent64, d_name\) \+ namlen \+ 1,\n'
    r'\s+sizeof\(u64\)\);\n\n)(\s+buf->error = -EINVAL)',
    r'\1'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC) &&\n'
    '\t    susfs_sus_ino_for_filldir64(ino)) {\n'
    '\t\treturn 0;\n'
    '\t}\n'
    '#endif\n'
    r'\2',
    'readdir.c: hunk#3 — filldir64 sus_path ino check')

# ── kernel/sys.c ──────────────────────────────────────────────────────────────
print("\n── kernel/sys.c ─────────────────────────────────────────────────────")

# FAILED at 1143: spoof_uname
# Upstream context: override_release at 1143 — Samsung has it at 1314.
# Samsung newuname uses "int errno = 0" + direct copy_to_user (confirmed from source).
# Restructure to use tmp buffer only when SPOOF_UNAME enabled, keep original in #else.

fix('kernel/sys.c',
    'SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)',
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    'extern void susfs_spoof_uname(struct new_utsname *tmp);\n'
    '#endif\n'
    'SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)',
    'sys.c: add susfs_spoof_uname extern before newuname')

fix('kernel/sys.c',
    '\tint errno = 0;\n'
    '\n'
    '\tdown_read(&uts_sem);\n'
    '\tif (copy_to_user(name, utsname(), sizeof *name))\n'
    '\t\terrno = -EFAULT;\n'
    '\tup_read(&uts_sem);',
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
    'sys.c: newuname spoof injection (Samsung int-errno variant)')

# ── fs/susfs.c ────────────────────────────────────────────────────────────────
print("\n── fs/susfs.c ───────────────────────────────────────────────────────")

# susfs_mnt_alloc_id is static in susfs.c but called from namespace.c via extern —
# must be non-static to be visible across translation units.
fix_regex('fs/susfs.c',
    r'^static int susfs_mnt_alloc_id\b',
    'int susfs_mnt_alloc_id',
    'susfs.c: make susfs_mnt_alloc_id non-static (called from namespace.c)')

# ── Skipped files ─────────────────────────────────────────────────────────────
print("\n── Skipped (all hunks already succeeded in patch) ───────────────────")
print("↩️  fs/notify/fdinfo.c  fs/stat.c  fs/statfs.c  kernel/kallsyms.c")
print("↩️  fs/overlayfs/overlayfs.h  fs/overlayfs/readdir.c  fs/overlayfs/super.c")
print("↩️  fs/proc/fd.c  fs/Makefile")
print("\n── Skipped (incompatible Samsung implementation) ────────────────────")
print("↩️  fs/overlayfs/inode.c   — ovl_path_lowerdata() absent in Samsung overlay")
print("↩️  fs/proc/cmdline.c      — Samsung has custom cmdline; SPOOF_CMDLINE=n")

print("\n✅ susfs_hunk_fix_note8.py complete")
