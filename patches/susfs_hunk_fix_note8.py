#!/usr/bin/env python3
# susfs_hunk_fix_note8.py — SUSFS v2.1.0 patch fixups for Samsung dreamlte 4.4
# Targets: ace2nutzer/Samsung_dreamlte_Kernel (SM-N950F, Exynos 8895, kernel 4.4.x)
# Run from kernel_source/ AFTER:
#   patch -p1 --fuzz=0 < susfs_4.9.patch
# Source patch: JackA1ltman/NonGKI_Kernel_Build_2nd susfs_patch_to_4.9.patch (SUSFS v2.1.0)
# All anchors verified against real dry-run/.rej output on this exact tree.

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

def fix_regex(path, pattern, replacement, label, flags=re.DOTALL):
    try:
        with open(path, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        print(f"⚠️  {label}: {path} not found — SKIP")
        return False
    if not re.search(pattern, s, flags):
        print(f"⚠️  {label}: pattern not found — already applied or mismatch")
        return False
    result = re.sub(pattern, replacement, s, count=1, flags=flags)
    if result == s:
        print(f"↩️  {label}: already applied — SKIP")
        return True
    with open(path, 'w') as f:
        f.write(result)
    print(f"✅ {label}")
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# fs/namei.c
# ═══════════════════════════════════════════════════════════════════════════════
print("══ fs/namei.c ══════════════════════════════════════════════════════════")

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
    'namei.c hunk#1: susfs_def.h include')

fix('fs/namei.c',
    '/* [Feb-1997 T. Schoebel-Theuer]',
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    'extern bool susfs_is_inode_sus_path(struct inode *inode);\n'
    'extern const struct qstr susfs_fake_qstr_name;\n'
    '#endif\n'
    '\n'
    '/* [Feb-1997 T. Schoebel-Theuer]',
    'namei.c hunk#2: susfs_is_inode_sus_path externs')

fix('fs/namei.c',
    '\t\t*need_lookup = true;\n'
    '\t}\n'
    '\treturn dentry;\n'
    '}',
    '\t\t*need_lookup = true;\n'
    '\t}\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif (dentry && !IS_ERR(dentry) && dentry->d_inode &&\n'
    '\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n'
    '\t\tdput(dentry);\n'
    '\t\t*need_lookup = true;\n'
    '\t\tdentry = d_alloc(dir, &susfs_fake_qstr_name);\n'
    '\t\tif (unlikely(!dentry))\n'
    '\t\t\treturn ERR_PTR(-ENOMEM);\n'
    '\t}\n'
    '#endif\n'
    '\treturn dentry;\n'
    '}',
    'namei.c hunk#5: lookup_dcache sus_path redirect to fake qstr')

print("↩️  namei.c hunk#7: __lookup_hash retry — not applicable (Samsung uses "
      "lookup_dcache+lookup_real, sus_path handled in hunk#5)")

fix('fs/namei.c',
    '\t\tdentry = __d_lookup_rcu(parent, &nd->last, &seq);\n'
    '\t\tif (!dentry)\n'
    '\t\t\tgoto unlazy;',
    '\t\tdentry = __d_lookup_rcu(parent, &nd->last, &seq);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\t{\n'
    '\t\t\tbool is_nd_state_lookup_last_and_open_last =\n'
    '\t\t\t\t(nd->state & (ND_STATE_LOOKUP_LAST | ND_STATE_OPEN_LAST));\n'
    '\t\t\tif (is_nd_state_lookup_last_and_open_last && dentry &&\n'
    '\t\t\t\t!IS_ERR(dentry) && dentry->d_inode &&\n'
    '\t\t\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n'
    '\t\t\t\t/* no dput() — __d_lookup_rcu does not take lockref */\n'
    '\t\t\t\tdentry = NULL;\n'
    '\t\t\t}\n'
    '\t\t}\n'
    '#endif\n'
    '\t\tif (!dentry)\n'
    '\t\t\tgoto unlazy;',
    'namei.c hunk#8: lookup_fast RCU path sus_path filter')

fix('fs/namei.c',
    '\t} else {\n'
    '\t\tdentry = __d_lookup(parent, &nd->last);\n'
    '\t}\n'
    '\n'
    '\tif (unlikely(!dentry))\n'
    '\t\tgoto need_lookup;',
    '\t} else {\n'
    '\t\tdentry = __d_lookup(parent, &nd->last);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\t{\n'
    '\t\t\tbool is_nd_state_lookup_last_and_open_last =\n'
    '\t\t\t\t(nd->state & (ND_STATE_LOOKUP_LAST | ND_STATE_OPEN_LAST));\n'
    '\t\t\tif (is_nd_state_lookup_last_and_open_last && dentry &&\n'
    '\t\t\t\t!IS_ERR(dentry) && dentry->d_inode &&\n'
    '\t\t\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n'
    '\t\t\t\tdput(dentry);\n'
    '\t\t\t\tdentry = NULL;\n'
    '\t\t\t}\n'
    '\t\t}\n'
    '#endif\n'
    '\t}\n'
    '\n'
    '\tif (unlikely(!dentry))\n'
    '\t\tgoto need_lookup;',
    'namei.c hunk#9: lookup_fast non-RCU path sus_path filter')

fix('fs/namei.c',
    '\tmutex_lock(&parent->d_inode->i_mutex);\n'
    '\tdentry = __lookup_hash(&nd->last, parent, nd->flags);\n'
    '\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\tif (IS_ERR(dentry))\n'
    '\t\treturn PTR_ERR(dentry);\n'
    '\tpath->mnt = nd->path.mnt;\n'
    '\tpath->dentry = dentry;\n'
    '\treturn follow_managed(path, nd);\n'
    '}',
    '\tmutex_lock(&parent->d_inode->i_mutex);\n'
    '\tdentry = __lookup_hash(&nd->last, parent, nd->flags);\n'
    '\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\tif (IS_ERR(dentry))\n'
    '\t\treturn PTR_ERR(dentry);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif ((nd->flags & ND_FLAGS_LOOKUP_LAST) &&\n'
    '\t\tdentry && dentry->d_inode &&\n'
    '\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n'
    '\t\tdput(dentry);\n'
    '\t\t/* redirect lookup to fake qstr to hide sus path */\n'
    '\t\tmutex_lock(&parent->d_inode->i_mutex);\n'
    '\t\tdentry = d_alloc(parent, &susfs_fake_qstr_name);\n'
    '\t\tif (!dentry) {\n'
    '\t\t\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\t\t\treturn -ENOMEM;\n'
    '\t\t}\n'
    '\t\tdentry = lookup_real(parent->d_inode, dentry, nd->flags);\n'
    '\t\tmutex_unlock(&parent->d_inode->i_mutex);\n'
    '\t\tif (IS_ERR(dentry))\n'
    '\t\t\treturn PTR_ERR(dentry);\n'
    '\t}\n'
    '#endif\n'
    '\tpath->mnt = nd->path.mnt;\n'
    '\tpath->dentry = dentry;\n'
    '\treturn follow_managed(path, nd);\n'
    '}',
    'namei.c hunks#10-13: lookup_slow sus_path redirect (Samsung mutex variant)')

fix('fs/namei.c',
    '\t\terr = lookup_slow(nd, &path);\n'
    '\t\tif (err < 0)\n'
    '\t\t\treturn err;',
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\tif (nd->state & ND_STATE_LOOKUP_LAST)\n'
    '\t\t\tnd->flags |= ND_FLAGS_LOOKUP_LAST;\n'
    '#endif\n'
    '\t\terr = lookup_slow(nd, &path);\n'
    '\t\tif (err < 0)\n'
    '\t\t\treturn err;',
    'namei.c hunk#14: walk_component ND_FLAGS_LOOKUP_LAST before lookup_slow')

# Hunk #15: regex-based due to irregular whitespace in upstream source
fix_regex('fs/namei.c',
    r'(\t\terr = may_lookup\(nd\);\n[ \t]+if \(err\)\n\t\t\treturn err;\n)\n(\t\thash_len = hash_name\(name\);)',
    r'\1\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\t\t{\n'
    '\t\t\tstruct dentry *dentry = nd->path.dentry;\n'
    '\t\t\tif (dentry->d_inode &&\n'
    '\t\t\t\tsusfs_is_inode_sus_path(dentry->d_inode))\n'
    '\t\t\t\treturn -ENOENT;\n'
    '\t\t}\n'
    '#endif\n\n'
    r'\2',
    'namei.c hunk#15: link_path_walk sus_path subpath check')

fix('fs/namei.c',
    '\tmutex_lock(&dir->d_inode->i_mutex);\n'
    '\tdentry = d_lookup(dir, &nd->last);\n'
    '\tif (!dentry) {\n'
    '\t\t/*\n'
    '\t\t * No cached dentry. Mounted dentries are pinned in the cache,\n'
    '\t\t * so that means that this dentry is probably a symlink or the\n'
    '\t\t * path doesn\'t actually point to a mounted dentry.\n'
    '\t\t */\n'
    '\t\tdentry = d_alloc(dir, &nd->last);',
    '\tmutex_lock(&dir->d_inode->i_mutex);\n'
    '\tdentry = d_lookup(dir, &nd->last);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tif ((nd->state & ND_STATE_OPEN_LAST) && dentry &&\n'
    '\t\t!IS_ERR(dentry) && dentry->d_inode &&\n'
    '\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n'
    '\t\tdput(dentry);\n'
    '\t\tdentry = d_alloc(dir, &susfs_fake_qstr_name);\n'
    '\t\tif (!dentry) {\n'
    '\t\t\tmutex_unlock(&dir->d_inode->i_mutex);\n'
    '\t\t\treturn -ENOMEM;\n'
    '\t\t}\n'
    '\t\tdentry = lookup_real(dir->d_inode, dentry, nd->flags);\n'
    '\t\tif (IS_ERR(dentry)) {\n'
    '\t\t\tmutex_unlock(&dir->d_inode->i_mutex);\n'
    '\t\t\treturn PTR_ERR(dentry);\n'
    '\t\t}\n'
    '\t\tgoto done_sus;\n'
    '\t}\n'
    '#endif\n'
    '\tif (!dentry) {\n'
    '\t\t/*\n'
    '\t\t * No cached dentry. Mounted dentries are pinned in the cache,\n'
    '\t\t * so that means that this dentry is probably a symlink or the\n'
    '\t\t * path doesn\'t actually point to a mounted dentry.\n'
    '\t\t */\n'
    '\t\tdentry = d_alloc(dir, &nd->last);',
    'namei.c hunk#16: do_last inline open sus_path redirect (Samsung variant)')

fix('fs/namei.c',
    '\tmutex_unlock(&dir->d_inode->i_mutex);\n'
    '\n'
    'done:\n'
    '\tif (d_is_negative(dentry)) {',
    '\tmutex_unlock(&dir->d_inode->i_mutex);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    'done_sus:\n'
    '#endif\n'
    '\n'
    'done:\n'
    '\tif (d_is_negative(dentry)) {',
    'namei.c hunk#16b: done_sus label before done: in do_last')

with open('fs/namei.c', 'r') as f:
    _s = f.read()
if 'ND_STATE_OPEN_LAST' in _s:
    print("↩️  namei.c hunk#18: ND_STATE_OPEN_LAST already applied by patch — SKIP")
else:
    fix('fs/namei.c',
        '\tnd->flags &= ~LOOKUP_PARENT;\n'
        '\tnd->flags |= op->intent;',
        '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
        '\tnd->state |= ND_STATE_OPEN_LAST;\n'
        '#endif\n'
        '\tnd->flags &= ~LOOKUP_PARENT;\n'
        '\tnd->flags |= op->intent;',
        'namei.c hunk#18: do_last ND_STATE_OPEN_LAST')

fix('fs/namei.c',
    'EXPORT_SYMBOL(readlink_copy);\n'
    '\n'
    '/*\n'
    ' * A helper for ->readlink().  This should be used *ONLY* for symlinks that\n'
    ' * have ->follow_link() touching nd only in nd_set_link().  Using (or not\n'
    ' * using) it for any given inode is up to filesystem.\n'
    ' */\n'
    'int generic_readlink(struct dentry *dentry, char __user *buffer, int buflen)',
    'EXPORT_SYMBOL(readlink_copy);\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern int susfs_open_redirect_spoof_vfs_readlink(struct inode *inode, '
    'char __user *buffer, int buflen);\n'
    '#endif\n'
    '\n'
    '/*\n'
    ' * A helper for ->readlink().  This should be used *ONLY* for symlinks that\n'
    ' * have ->follow_link() touching nd only in nd_set_link().  Using (or not\n'
    ' * using) it for any given inode is up to filesystem.\n'
    ' */\n'
    'int generic_readlink(struct dentry *dentry, char __user *buffer, int buflen)',
    'namei.c hunk#20: susfs_open_redirect_spoof_vfs_readlink extern')

fix('fs/namei.c',
    '\tres = readlink_copy(buffer, buflen, link);\n'
    '\tif (inode->i_op->put_link)\n'
    '\t\tinode->i_op->put_link(inode, cookie);\n'
    '\treturn res;\n'
    '}\n'
    'EXPORT_SYMBOL(generic_readlink);',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tif (SUSFS_IS_INODE_OPEN_REDIRECT(inode)) {\n'
    '\t\tint redir_res = susfs_open_redirect_spoof_vfs_readlink(\n'
    '\t\t\tinode, buffer, buflen);\n'
    '\t\tif (!redir_res) {\n'
    '\t\t\tif (inode->i_op->put_link)\n'
    '\t\t\t\tinode->i_op->put_link(inode, cookie);\n'
    '\t\t\treturn redir_res;\n'
    '\t\t}\n'
    '\t}\n'
    '#endif\n'
    '\tres = readlink_copy(buffer, buflen, link);\n'
    '\tif (inode->i_op->put_link)\n'
    '\t\tinode->i_op->put_link(inode, cookie);\n'
    '\treturn res;\n'
    '}\n'
    'EXPORT_SYMBOL(generic_readlink);',
    'namei.c hunk#21: generic_readlink OPEN_REDIRECT spoof (Samsung put_link API)')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/namespace.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/namespace.c ═══════════════════════════════════════════════════════")

fix('fs/namespace.c',
    '#include "pnode.h"\n'
    '#include "internal.h"',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#include "pnode.h"\n'
    '#include "internal.h"\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'extern bool susfs_is_current_ksu_domain(void);\n'
    'extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;\n'
    '#define CL_COPY_MNT_NS BIT(25)\n'
    '#endif',
    'namespace.c hunk#1: susfs includes + externs')

# ── fs/namespace.c — susfs_alloc_{un,non_un}share_ksu_vfsmnt function bodies ──
# (Samsung is CONFIG_SMP — must use mnt_pcp, not flat mnt_count/mnt_writers)
_anchor = "static struct mount *alloc_vfsmnt(const char *name)"
_funcs = (
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '/* A copy of alloc_vfsmnt() but allocates the fake mnt_id for mounts\n'
    ' * that are unshared by ksu process\n'
    ' */\n'
    'static struct mount *susfs_alloc_unshare_ksu_vfsmnt(const char *name, int old_mnt_id)\n'
    '{\n'
    '\tstruct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);\n'
    '\n'
    '\tif (mnt) {\n'
    '\t\tmnt->mnt_id = old_mnt_id;\n'
    '\n'
    '\t\tif (name) {\n'
    '\t\t\tmnt->mnt_devname = kstrdup_const(name, GFP_KERNEL);\n'
    '\t\t\tif (!mnt->mnt_devname)\n'
    '\t\t\t\tgoto out_free_cache;\n'
    '\t\t}\n'
    '#ifdef CONFIG_SMP\n'
    '\t\tmnt->mnt_pcp = alloc_percpu(struct mnt_pcp);\n'
    '\t\tif (!mnt->mnt_pcp)\n'
    '\t\t\tgoto out_free_devname;\n'
    '\t\tthis_cpu_add(mnt->mnt_pcp->mnt_count, 1);\n'
    '#else\n'
    '\t\tmnt->mnt_count = 1;\n'
    '\t\tmnt->mnt_writers = 0;\n'
    '#endif\n'
    '\n'
    '\t\tINIT_HLIST_NODE(&mnt->mnt_hash);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_child);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_mounts);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_expire);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_share);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_slave_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_slave);\n'
    '\t\tINIT_HLIST_NODE(&mnt->mnt_mp_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_umounting);\n'
    '\t\tinit_fs_pin(&mnt->mnt_umount, drop_mountpoint);\n'
    '\t}\n'
    '\treturn mnt;\n'
    '\n'
    '#ifdef CONFIG_SMP\n'
    'out_free_devname:\n'
    '\tkfree_const(mnt->mnt_devname);\n'
    '#endif\n'
    'out_free_cache:\n'
    '\tkmem_cache_free(mnt_cache, mnt);\n'
    '\treturn NULL;\n'
    '}\n'
    '\n'
    '/* A copy of alloc_vfsmnt() but allocates the fake mnt_id for mount\n'
    ' * that is mounted or single cloned by ksu process\n'
    ' */\n'
    'static struct mount *susfs_alloc_non_unshare_ksu_vfsmnt(const char *name)\n'
    '{\n'
    '\tstruct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);\n'
    '\tint res;\n'
    '\n'
    '\tif (mnt) {\n'
    '\t\tres = ida_simple_get(&mnt_id_ida, DEFAULT_KSU_MNT_ID, 0, GFP_KERNEL);\n'
    '\t\tif (res < 0)\n'
    '\t\t\tgoto out_free_cache;\n'
    '\n'
    '\t\tmnt->mnt_id = res;\n'
    '\n'
    '\t\tif (name) {\n'
    '\t\t\tmnt->mnt_devname = kstrdup_const(name, GFP_KERNEL);\n'
    '\t\t\tif (!mnt->mnt_devname)\n'
    '\t\t\t\tgoto out_free_id;\n'
    '\t\t}\n'
    '#ifdef CONFIG_SMP\n'
    '\t\tmnt->mnt_pcp = alloc_percpu(struct mnt_pcp);\n'
    '\t\tif (!mnt->mnt_pcp)\n'
    '\t\t\tgoto out_free_devname;\n'
    '\t\tthis_cpu_add(mnt->mnt_pcp->mnt_count, 1);\n'
    '#else\n'
    '\t\tmnt->mnt_count = 1;\n'
    '\t\tmnt->mnt_writers = 0;\n'
    '#endif\n'
    '\n'
    '\t\tINIT_HLIST_NODE(&mnt->mnt_hash);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_child);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_mounts);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_expire);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_share);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_slave_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_slave);\n'
    '\t\tINIT_HLIST_NODE(&mnt->mnt_mp_list);\n'
    '\t\tINIT_LIST_HEAD(&mnt->mnt_umounting);\n'
    '\t\tinit_fs_pin(&mnt->mnt_umount, drop_mountpoint);\n'
    '\t}\n'
    '\treturn mnt;\n'
    '\n'
    '#ifdef CONFIG_SMP\n'
    'out_free_devname:\n'
    '\tkfree_const(mnt->mnt_devname);\n'
    '#endif\n'
    'out_free_id:\n'
    '\tmnt_free_id(mnt);\n'
    'out_free_cache:\n'
    '\tkmem_cache_free(mnt_cache, mnt);\n'
    '\treturn NULL;\n'
    '}\n'
    '#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\n'
)
fix('fs/namespace.c', _anchor, _funcs + _anchor,
    'namespace.c: susfs_alloc_{un,non_un}share_ksu_vfsmnt function bodies (SMP-correct)')

fix('fs/namespace.c',
    'static int mnt_alloc_group_id(struct mount *mnt)\n'
    '{\n'
    '\tint res;\n'
    '\n'
    '\tif (!ida_pre_get(&mnt_group_ida, GFP_KERNEL))\n'
    '\t\treturn -ENOMEM;\n'
    '\n'
    '\tres = ida_get_new_above(&mnt_group_ida,\n'
    '\t\t\t\tmnt_group_start,\n'
    '\t\t\t\t&mnt->mnt_group_id);',
    'static int mnt_alloc_group_id(struct mount *mnt)\n'
    '{\n'
    '\tint res;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (susfs_is_current_ksu_domain()) {\n'
    '\t\tif (!ida_pre_get(&mnt_group_ida, GFP_KERNEL))\n'
    '\t\t\treturn -ENOMEM;\n'
    '\t\tres = ida_get_new_above(&mnt_group_ida,\n'
    '\t\t\t\t\tDEFAULT_KSU_MNT_GROUP_ID,\n'
    '\t\t\t\t\t&mnt->mnt_group_id);\n'
    '\t\tgoto bypass_orig_flow;\n'
    '\t}\n'
    '#endif\n'
    '\tif (!ida_pre_get(&mnt_group_ida, GFP_KERNEL))\n'
    '\t\treturn -ENOMEM;\n'
    '\n'
    '\tres = ida_get_new_above(&mnt_group_ida,\n'
    '\t\t\t\tmnt_group_start,\n'
    '\t\t\t\t&mnt->mnt_group_id);',
    'namespace.c hunk#5: mnt_alloc_group_id KSU domain high group id')

fix('fs/namespace.c',
    '\tres = ida_get_new_above(&mnt_group_ida,\n'
    '\t\t\t\tmnt_group_start,\n'
    '\t\t\t\t&mnt->mnt_group_id);\n'
    '\tif (!res)\n'
    '\t\tmnt_group_start = mnt->mnt_group_id + 1;',
    '\tres = ida_get_new_above(&mnt_group_ida,\n'
    '\t\t\t\tmnt_group_start,\n'
    '\t\t\t\t&mnt->mnt_group_id);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'bypass_orig_flow:\n'
    '#endif\n'
    '\tif (!res)\n'
    '\t\tmnt_group_start = mnt->mnt_group_id + 1;',
    'namespace.c hunk#5b: mnt_alloc_group_id bypass label')

with open('fs/namespace.c', 'r') as f:
    _ns = f.read()
if 'susfs_alloc_non_unshare_ksu_vfsmnt' in _ns and \
   'bypass_orig_flow' in _ns and \
   'susfs_is_sdcard_android_data_not_decrypted' in _ns:
    if 'static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)' in _ns:
        print("↩️  namespace.c hunk#7: vfs_kern_mount KSU intercept already applied — SKIP")
    else:
        fix('fs/namespace.c',
            '\tmnt = alloc_vfsmnt(name);\n'
            '\tif (!mnt)\n'
            '\t\treturn ERR_PTR(-ENOMEM);',
            '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
            '\tif (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {\n'
            '\t\tif (susfs_is_current_ksu_domain()) {\n'
            '\t\t\tmnt = susfs_alloc_non_unshare_ksu_vfsmnt(name ?: "none");\n'
            '\t\t\tgoto bypass_alloc;\n'
            '\t\t}\n'
            '\t}\n'
            '#endif\n'
            '\tmnt = alloc_vfsmnt(name);\n'
            '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
            'bypass_alloc:\n'
            '#endif\n'
            '\tif (!mnt)\n'
            '\t\treturn ERR_PTR(-ENOMEM);',
            'namespace.c hunk#7: vfs_kern_mount KSU domain fake mnt_id')
else:
    print("⚠️  namespace.c hunk#7: patch hunks #2-#6 may not have applied — check manually")

fix('fs/namespace.c',
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n'
    '\tif (!mnt)\n'
    '\t\treturn ERR_PTR(-ENOMEM);',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {\n'
    '\t\tif (susfs_is_current_ksu_domain()) {\n'
    '\t\t\tif (flag & CL_COPY_MNT_NS)\n'
    '\t\t\t\tmnt = susfs_alloc_unshare_ksu_vfsmnt(\n'
    '\t\t\t\t\told->mnt_devname, old->mnt_id);\n'
    '\t\t\telse\n'
    '\t\t\t\tmnt = susfs_alloc_non_unshare_ksu_vfsmnt(\n'
    '\t\t\t\t\told->mnt_devname);\n'
    '\t\t\tgoto bypass_clone_alloc;\n'
    '\t\t}\n'
    '\t}\n'
    '\tif (old->mnt_id >= DEFAULT_KSU_MNT_ID) {\n'
    '\t\tmnt = susfs_alloc_non_unshare_ksu_vfsmnt(old->mnt_devname);\n'
    '\t\tgoto bypass_clone_alloc;\n'
    '\t}\n'
    '#endif\n'
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'bypass_clone_alloc:\n'
    '#endif\n'
    '\tif (!mnt)\n'
    '\t\treturn ERR_PTR(-ENOMEM);',
    'namespace.c hunk#8: clone_mnt KSU domain alloc intercept')

fix('fs/namespace.c',
    '\tmnt->mnt.mnt_flags = old->mnt.mnt_flags & ~(MNT_WRITE_HOLD|MNT_MARKED);\n'
    '\t/* Don\'t allow unprivileged users to change mount flags */',
    '\tmnt->mnt.mnt_flags = old->mnt.mnt_flags & ~(MNT_WRITE_HOLD|MNT_MARKED);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (unlikely((flag & CL_COPY_MNT_NS) &&\n'
    '\t\t\tsusfs_is_current_ksu_domain() &&\n'
    '\t\t\tstatic_branch_unlikely(\n'
    '\t\t\t\t&susfs_is_sdcard_android_data_not_decrypted)))\n'
    '\t\tmnt->mnt.mnt_flags |= VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT;\n'
    '#endif\n'
    '\t/* Don\'t allow unprivileged users to change mount flags */',
    'namespace.c hunk#9: clone_mnt VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT (Samsung non-RKP branch)')

fix('fs/namespace.c',
    '\tcopy_flags = CL_COPY_UNBINDABLE | CL_EXPIRE;\n'
    '\tif (user_ns != ns->user_ns)\n'
    '\t\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;',
    '\tcopy_flags = CL_COPY_UNBINDABLE | CL_EXPIRE;\n'
    '\tif (user_ns != ns->user_ns)\n'
    '\t\tcopy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tcopy_flags |= CL_COPY_MNT_NS;\n'
    '#endif',
    'namespace.c hunk#11: copy_mnt_ns CL_COPY_MNT_NS flag')

fix('fs/namespace.c',
    'static void mnt_free_id(struct mount *mnt)\n'
    '{\n'
    '\tint id = mnt->mnt_id;\n'
    '\tspin_lock(&mnt_id_lock);',
    'static void mnt_free_id(struct mount *mnt)\n'
    '{\n'
    '\tint id = mnt->mnt_id;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tif (mnt->mnt.mnt_flags & VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT)\n'
    '\t\treturn;\n'
    '#endif\n'
    '\tspin_lock(&mnt_id_lock);',
    'namespace.c hunk#13: mnt_free_id skip KSU unshared mounts')

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
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '/* - To retrieve the non sus mnt_id from mount */\n'
    'int susfs_get_non_sus_mnt_id_from_mnt(struct mount *orig_mnt) {\n'
    '\tstruct mount *mnt = orig_mnt;\n'
    '\tint mnt_id;\n'
    '\n'
    '\tlock_mount_hash();\n'
    '\tfor (; mnt && mnt->mnt_parent && mnt != mnt->mnt_parent && '
    'mnt->mnt_id >= DEFAULT_KSU_MNT_ID; mnt = mnt->mnt_parent) { }\n'
    '\tmnt_id = mnt->mnt_id;\n'
    '\tunlock_mount_hash();\n'
    '\treturn mnt_id;\n'
    '}\n'
    '\n'
    '/* - To retrieve the non sus vfsmount from vfsmount, takes a reference '
    'on \\&mnt->mnt and mnt->mnt.mnt_root */\n'
    'struct vfsmount *susfs_get_non_sus_vfsmnt_from_vfsmnt(struct vfsmount *vfsmnt) {\n'
    '\tstruct mount *mnt = real_mount(vfsmnt);\n'
    '\n'
    '\tlock_mount_hash();\n'
    '\tfor (; mnt && mnt->mnt_parent && mnt != mnt->mnt_parent && '
    'mnt->mnt_id >= DEFAULT_KSU_MNT_ID; mnt = mnt->mnt_parent) { }\n'
    '\tmntget(&mnt->mnt);\n'
    '\tif (!mnt->mnt.mnt_root || IS_ERR(mnt->mnt.mnt_root)) {\n'
    '\t\tmntput(&mnt->mnt);\n'
    '\t\tunlock_mount_hash();\n'
    '\t\treturn vfsmnt;\n'
    '\t}\n'
    '\tdget(mnt->mnt.mnt_root);\n'
    '\tunlock_mount_hash();\n'
    '\treturn &mnt->mnt;\n'
    '}\n'
    '#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT',
    'namespace.c hunk#14: EOF helper functions')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/notify/fdinfo.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/notify/fdinfo.c ═══════════════════════════════════════════════════")
fix('fs/notify/fdinfo.c',
    'static void inotify_fdinfo(struct seq_file *m, struct fsnotify_mark *mark)\n'
    '{\n'
    '\tstruct inotify_inode_mark *inode_mark;\n'
    '\tstruct inode *inode;',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    'static void inotify_fdinfo(struct seq_file *m, struct fsnotify_mark *mark,\n'
    '\t\t\t   struct file *file)\n'
    '#else\n'
    'static void inotify_fdinfo(struct seq_file *m, struct fsnotify_mark *mark)\n'
    '#endif\n'
    '{\n'
    '\tstruct inotify_inode_mark *inode_mark;\n'
    '\tstruct inode *inode;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\tstruct mount *mnt = NULL;\n'
    '#endif',
    'fdinfo.c hunk#4: inotify_fdinfo signature + mnt var')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/open.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/open.c ════════════════════════════════════════════════════════════")

fix('fs/open.c',
    '#include <linux/personality.h>',
    '#include <linux/personality.h>\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '#include <linux/susfs_def.h>\n'
    '#endif',
    'open.c: susfs_def.h include')

fix('fs/open.c',
    'long do_sys_open(int dfd, const char __user *filename, int flags, umode_t mode)\n'
    '{\n'
    '\tstruct open_flags op;\n'
    '\tint fd = build_open_flags(flags, mode, &op);\n'
    '\tstruct filename *tmp;',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern struct filename *susfs_open_redirect_spoof_do_sys_openat(\n'
    '\tstruct inode *inode);\n'
    '#endif\n'
    'long do_sys_open(int dfd, const char __user *filename, int flags, umode_t mode)\n'
    '{\n'
    '\tstruct open_flags op;\n'
    '\tint fd = build_open_flags(flags, mode, &op);\n'
    '\tstruct filename *tmp;\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tstruct filename *fake_filename = NULL;\n'
    '\tbool is_inode_open_redirect = false;\n'
    '#endif',
    'open.c hunk#1: do_sys_open OPEN_REDIRECT extern + vars')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/proc/base.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/proc/base.c ═══════════════════════════════════════════════════════")
fix('fs/proc/base.c',
    '#include <linux/posix-timers.h>\n'
    '#ifdef CONFIG_HARDWALL',
    '#include <linux/posix-timers.h>\n'
    '#if defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '#ifdef CONFIG_HARDWALL',
    'proc/base.c hunk#1: susfs_def.h include (posix-timers.h anchor)')

fix('fs/proc/base.c',
    'static int do_proc_readlink(struct path *path, char __user *buffer, int buflen)\n'
    '{',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern int susfs_open_redirect_spoof_do_proc_readlink(struct inode *inode, '
    'char *tmp_buf, int buflen);\n'
    '#endif\n'
    'static int do_proc_readlink(struct path *path, char __user *buffer, int buflen)\n'
    '{',
    'proc/base.c: do_proc_readlink OPEN_REDIRECT extern')

fix('fs/proc/base.c',
    '\tif (!tmp)\n'
    '\t\treturn -ENOMEM;\n'
    '\n'
    '\tpathname = d_path(path, tmp, PAGE_SIZE);',
    '\tif (!tmp)\n'
    '\t\treturn -ENOMEM;\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    '\tif (SUSFS_IS_INODE_OPEN_REDIRECT(path->dentry->d_inode)) {\n'
    '\t\tif (!susfs_open_redirect_spoof_do_proc_readlink(\n'
    '\t\t\tpath->dentry->d_inode, tmp, buflen)) {\n'
    '\t\t\tint len = strlen(tmp);\n'
    '\t\t\tif (copy_to_user(buffer, tmp, len))\n'
    '\t\t\t\tlen = -EFAULT;\n'
    '\t\t\tfree_page((unsigned long)tmp);\n'
    '\t\t\treturn len;\n'
    '\t\t}\n'
    '\t}\n'
    '#endif\n'
    '\tpathname = d_path(path, tmp, PAGE_SIZE);',
    'proc/base.c: do_proc_readlink OPEN_REDIRECT spoof body')

fix('fs/proc/base.c',
    '\t\t\tif (!vma->vm_file)\n'
    '\t\t\t\tcontinue;\n'
    '\t\t\tif (++pos <= ctx->pos)\n'
    '\t\t\t\tcontinue;',
    '\t\t\tif (!vma->vm_file)\n'
    '\t\t\t\tcontinue;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\t\t\tif (SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n'
    '\t\t\t\tcontinue;\n'
    '#endif\n'
    '\t\t\tif (++pos <= ctx->pos)\n'
    '\t\t\t\tcontinue;',
    'proc/base.c: proc_map_files_readdir SUS_MAP skip')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/proc/cmdline.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/proc/cmdline.c ════════════════════════════════════════════════════")
fix('fs/proc/cmdline.c',
    'static int cmdline_proc_show(struct seq_file *m, void *v)\n'
    '{',
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG\n'
    'extern struct static_key_false susfs_is_fake_cmdline_or_bootconfig_buffer_set;\n'
    'extern void susfs_spoof_cmdline_or_bootconfig(struct seq_file *m);\n'
    '#endif\n'
    'static int cmdline_proc_show(struct seq_file *m, void *v)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG\n'
    '\tif (static_branch_likely(&susfs_is_fake_cmdline_or_bootconfig_buffer_set)) {\n'
    '\t\tsusfs_spoof_cmdline_or_bootconfig(m);\n'
    '\t\tseq_printf(m, "%s\\n", "");\n'
    '\t\treturn 0;\n'
    '\t}\n'
    '#endif',
    'cmdline.c hunks#1+2: SPOOF_CMDLINE externs + check')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/proc/task_mmu.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/proc/task_mmu.c ═══════════════════════════════════════════════════")
fix('fs/proc/task_mmu.c',
    '#include <linux/sched/mm.h>\n'
    '\n'
    '#include <asm/elf.h>',
    '#include <linux/sched/mm.h>\n'
    '#if defined(CONFIG_KSU_SUSFS_SUS_KSTAT) || defined(CONFIG_KSU_SUSFS_SUS_MAP) '
    '|| defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '\n'
    '#include <asm/elf.h>',
    'task_mmu.c hunk#1: susfs_def.h include (sched/mm.h anchor)')

fix('fs/proc/task_mmu.c',
    'static void\n'
    'show_map_vma(struct seq_file *m, struct vm_area_struct *vma, int is_pid)\n'
    '{',
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    'extern void susfs_sus_kstat_spoof_show_map_vma(struct inode *inode, '
    'dev_t *out_dev, unsigned long *out_ino);\n'
    '#endif\n'
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern int susfs_open_redirect_spoof_show_map_vma(struct inode *inode, '
    'unsigned long *out_ino, dev_t *out_dev, char *spoofed_name);\n'
    '#endif\n'
    'static void\n'
    'show_map_vma(struct seq_file *m, struct vm_area_struct *vma, int is_pid)\n'
    '{',
    'task_mmu.c hunk#2: show_map_vma externs')

fix('fs/proc/task_mmu.c',
    '\tif (file) {\n'
    '\t\tstruct inode *inode = file_inode(vma->vm_file);\n'
    '\t\tdev = inode->i_sb->s_dev;\n'
    '\t\tino = inode->i_ino;',
    '\tif (file) {\n'
    '\t\tstruct inode *inode = file_inode(vma->vm_file);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\t\tif (SUSFS_IS_INODE_SUS_MAP(inode))\n'
    '\t\t\treturn;\n'
    '#endif\n'
    '\t\tdev = inode->i_sb->s_dev;\n'
    '\t\tino = inode->i_ino;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '\t\tsusfs_sus_kstat_spoof_show_map_vma(inode, &dev, &ino);\n'
    '#endif',
    'task_mmu.c hunks#3-5: SUS_MAP return + SUS_KSTAT spoof in show_map_vma')

fix('fs/proc/task_mmu.c',
    '\tshow_map_vma(m, vma, is_pid);\n'
    '\n'
    '\tif (vma_get_anon_name(vma)) {',
    '\tshow_map_vma(m, vma, is_pid);\n'
    '\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\tif (vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n'
    '\t\tgoto bypass_smap_body;\n'
    '#endif\n'
    '\n'
    '\tif (vma_get_anon_name(vma)) {',
    'task_mmu.c hunk#7: show_smap SUS_MAP skip whole body (Samsung, no rollup_mode)')

fix('fs/proc/task_mmu.c',
    '\tshow_smap_vma_flags(m, vma);\n'
    '\tm_cache_vma(m, vma);\n'
    '\treturn 0;\n'
    '}\n'
    '\n'
    'static int show_pid_smap(struct seq_file *m, void *v)',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\tgoto skip_smap_flags;\n'
    'bypass_smap_body:\n'
    '#endif\n'
    '\tshow_smap_vma_flags(m, vma);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    'skip_smap_flags:\n'
    '#endif\n'
    '\tm_cache_vma(m, vma);\n'
    '\treturn 0;\n'
    '}\n'
    '\n'
    'static int show_pid_smap(struct seq_file *m, void *v)',
    'task_mmu.c hunk#8: show_smap SUS_MAP bypass labels')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/proc_namespace.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/proc_namespace.c ══════════════════════════════════════════════════")
fix('fs/proc_namespace.c',
    '#include "pnode.h"\n'
    '#include "internal.h"',
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '#include <linux/susfs_def.h>\n'
    'extern bool susfs_is_current_ksu_domain(void);\n'
    'extern bool susfs_hide_sus_mnts_for_non_su_procs;\n'
    '#endif\n'
    '#include "pnode.h"\n'
    '#include "internal.h"',
    'proc_namespace.c: includes + externs')

fix('fs/proc_namespace.c',
    'static int show_vfsmnt(struct seq_file *m, struct vfsmount *mnt)\n'
    '{',
    'static int show_vfsmnt(struct seq_file *m, struct vfsmount *mnt)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\t{\n'
    '\t\tstruct mount *r = real_mount(mnt);\n'
    '\t\tif (READ_ONCE(susfs_hide_sus_mnts_for_non_su_procs) &&\n'
    '\t\t\tr->mnt_id >= DEFAULT_KSU_MNT_ID &&\n'
    '\t\t\t!susfs_is_current_ksu_domain())\n'
    '\t\t\treturn 0;\n'
    '\t}\n'
    '#endif',
    'proc_namespace.c hunk#2: show_vfsmnt sus_mount filter')

fix('fs/proc_namespace.c',
    'static int show_mountinfo(struct seq_file *m, struct vfsmount *mnt)\n'
    '{',
    'static int show_mountinfo(struct seq_file *m, struct vfsmount *mnt)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\t{\n'
    '\t\tstruct mount *r = real_mount(mnt);\n'
    '\t\tif (READ_ONCE(susfs_hide_sus_mnts_for_non_su_procs) &&\n'
    '\t\t\tr->mnt_id >= DEFAULT_KSU_MNT_ID &&\n'
    '\t\t\t!susfs_is_current_ksu_domain())\n'
    '\t\t\treturn 0;\n'
    '\t}\n'
    '#endif',
    'proc_namespace.c hunk#3: show_mountinfo sus_mount filter')

fix('fs/proc_namespace.c',
    'static int show_vfsstat(struct seq_file *m, struct vfsmount *mnt)\n'
    '{',
    'static int show_vfsstat(struct seq_file *m, struct vfsmount *mnt)\n'
    '{\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '\t{\n'
    '\t\tstruct mount *r = real_mount(mnt);\n'
    '\t\tif (READ_ONCE(susfs_hide_sus_mnts_for_non_su_procs) &&\n'
    '\t\t\tr->mnt_id >= DEFAULT_KSU_MNT_ID &&\n'
    '\t\t\t!susfs_is_current_ksu_domain())\n'
    '\t\t\treturn 0;\n'
    '\t}\n'
    '#endif',
    'proc_namespace.c hunk#4: show_vfsstat sus_mount filter')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/readdir.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/readdir.c ═════════════════════════════════════════════════════════")

fix('fs/readdir.c',
    '\tcontainer_of(ctx, struct getdents_callback, ctx);\n'
    '\tunsigned long d_ino;\n',
    '\tcontainer_of(ctx, struct getdents_callback, ctx);\n'
    '\tunsigned long d_ino;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tstruct inode *inode;\n'
    '#endif\n',
    'readdir.c: filldir inode local var')

fix('fs/readdir.c',
    '\tstruct linux_dirent64 __user * current_dir;\n',
    '\tstruct linux_dirent64 __user * current_dir;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tstruct super_block *sb;\n'
    '#endif\n',
    'readdir.c: getdents_callback64 sb member')

fix('fs/readdir.c',
    '\tcontainer_of(ctx, struct getdents_callback64, ctx);\n'
    '\tint reclen = ALIGN(offsetof(struct linux_dirent64, d_name) + namlen + 1,\n',
    '\tcontainer_of(ctx, struct getdents_callback64, ctx);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '\tstruct inode *inode;\n'
    '#endif\n'
    '\tint reclen = ALIGN(offsetof(struct linux_dirent64, d_name) + namlen + 1,\n',
    'readdir.c: filldir64 inode local var')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/stat.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/stat.c ════════════════════════════════════════════════════════════")
fix('fs/stat.c',
    '#include <asm/unistd.h>',
    '#include <asm/unistd.h>\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    'extern void susfs_sus_kstat_spoof_generic_fillattr(struct inode *inode, '
    'struct kstat *stat);\n'
    '#endif',
    'stat.c hunk#1: SUS_KSTAT extern (Samsung asm/unistd anchor)')

fix('fs/stat.c',
    '\tstat->blksize = i_blocksize(inode);\n'
    '\tstat->blocks = inode->i_blocks;\n'
    '}',
    '\tstat->blksize = i_blocksize(inode);\n'
    '\tstat->blocks = inode->i_blocks;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '\tsusfs_sus_kstat_spoof_generic_fillattr(inode, stat);\n'
    '#endif\n'
    '}',
    'stat.c hunk#2: generic_fillattr SUS_KSTAT spoof call')

print("↩️  stat.c hunk#3: covered by hunk#2 (generic_fillattr spoof call) — SKIP")

# ═══════════════════════════════════════════════════════════════════════════════
# kernel/sys.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ kernel/sys.c ══════════════════════════════════════════════════════════")
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
    'extern struct static_key_false susfs_is_uname_spoof_buffer_set;\n'
    'extern void susfs_spoof_uname(struct new_utsname *tmp);\n'
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
    '\tif (static_branch_likely(&susfs_is_uname_spoof_buffer_set))\n'
    '\t\tsusfs_spoof_uname(&tmp);\n'
    '\tup_read(&uts_sem);\n'
    '\tif (copy_to_user(name, &tmp, sizeof(tmp)))\n'
    '\t\terrno = -EFAULT;\n'
    '#else\n'
    '\tif (copy_to_user(name, utsname(), sizeof *name))\n'
    '\t\terrno = -EFAULT;\n'
    '\tup_read(&uts_sem);\n'
    '#endif',
    'sys.c hunk#1: newuname int-errno variant with SPOOF_UNAME (Samsung real variant)')

# ═══════════════════════════════════════════════════════════════════════════════
# mm/memory.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ mm/memory.c ══════════════════════════════════════════════════════════")
fix('mm/memory.c',
    '#include <asm/pgtable.h>\n'
    '\n'
    '#include "internal.h"',
    '#include <asm/pgtable.h>\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '#include <linux/susfs_def.h>\n'
    '#endif\n'
    '\n'
    '#include "internal.h"',
    'memory.c hunk#1: susfs_def.h include (asm/pgtable anchor)')

fix('mm/memory.c',
    'int __access_remote_vm(struct task_struct *tsk, struct mm_struct *mm,\n'
    '\t\tunsigned long addr, void *buf, int len, int write)\n'
    '{\n'
    '\tstruct vm_area_struct *vma;\n'
    '\tvoid *old_buf = buf;',
    'int __access_remote_vm(struct task_struct *tsk, struct mm_struct *mm,\n'
    '\t\tunsigned long addr, void *buf, int len, int write)\n'
    '{\n'
    '\tstruct vm_area_struct *vma;\n'
    '\tvoid *old_buf = buf;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\tvma = find_vma(mm, addr);\n'
    '#endif',
    'memory.c hunk#2: __access_remote_vm vma prefetch for SUS_MAP')

fix('mm/memory.c',
    '\tdown_read(&mm->mmap_sem);\n'
    '\t/* ignore errors, just check how much was successfully transferred */\n'
    '\twhile (len) {',
    '\tdown_read(&mm->mmap_sem);\n'
    '\t/* ignore errors, just check how much was successfully transferred */\n'
    '\twhile (len) {\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n'
    '\t\tif (vma && vma->vm_file &&\n'
    '\t\t\tSUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n'
    '\t\t\tbreak;\n'
    '#endif',
    'memory.c hunk#3: __access_remote_vm SUS_MAP break')

# ═══════════════════════════════════════════════════════════════════════════════
# fs/susfs.c
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ fs/susfs.c ═══════════════════════════════════════════════════════════")
with open('fs/susfs.c', 'r') as f:
    _sc = f.read()
if 'extern bool susfs_is_current_ksu_domain(void);' in _sc:
    print("✅ susfs.c: susfs_is_current_ksu_domain correctly declared extern")
else:
    print("⚠️  susfs.c: check susfs_is_current_ksu_domain declaration")

# ═══════════════════════════════════════════════════════════════════════════════
# include/linux/susfs_def.h
# ═══════════════════════════════════════════════════════════════════════════════
print("\n══ include/linux/susfs_def.h ════════════════════════════════════════════")
fix('include/linux/susfs_def.h',
    '#include <linux/bits.h>',
    '#include <linux/bitops.h>',
    'susfs_def.h: bits.h → bitops.h (not in 4.4)')

print("\n✅ susfs_hunk_fix_note8.py complete")
print("Next: check build errors, then iterate on any remaining mismatches")
