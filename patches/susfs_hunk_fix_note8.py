def fix(file_path, search, replace, desc):
    with open(file_path, 'r') as f:
        content = f.read()
    if search not in content:
        print(f"FAILED: {desc} - Anchor not found.")
        return
    with open(file_path, 'w') as f:
        f.write(content.replace(search, replace))
    print(f"SUCCESS: {desc}")

# 1. fs/dcache.c
fix('fs/dcache.c',
    '                seq = raw_seqcount_begin(&dentry->d_seq);\n'
    '                if (dentry->d_parent != parent)\n'
    '                        continue;',
    '                seq = raw_seqcount_begin(&dentry->d_seq);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
    '                if (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC))\n'
    '                        continue;\n'
    '#endif\n'
    '                if (dentry->d_parent != parent)\n'
    '                        continue;',
    'dcache.c: __d_lookup_rcu anchor')

# 2. fs/namei.c - do_filp_open injection
# Targets the start of the function for the redirect check
fix('fs/namei.c',
    '        set_nameidata(&nd, dfd, pathname);\n'
    '        filp = path_openat(&nd, op, flags | LOOKUP_RCU);',
    '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
    'extern struct filename* susfs_get_redirected_path(unsigned long ino);\n'
    '#endif\n'
    '        set_nameidata(&nd, dfd, pathname);\n'
    '        filp = path_openat(&nd, op, flags | LOOKUP_RCU);',
    'namei.c: do_filp_open header injection')

# 3. kernel/sys.c - newuname spoofing
fix('kernel/sys.c',
    '        down_read(&uts_sem);\n'
    '        if (copy_to_user(name, utsname(), sizeof *name))\n'
    '                errno = -EFAULT;\n'
    '        up_read(&uts_sem);',
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    'extern void susfs_spoof_uname(struct new_utsname* tmp);\n'
    '#endif\n'
    '        down_read(&uts_sem);\n'
    '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
    '        {\n'
    '                struct new_utsname tmp;\n'
    '                memcpy(&tmp, utsname(), sizeof(tmp));\n'
    '                susfs_spoof_uname(&tmp);\n'
    '                if (copy_to_user(name, &tmp, sizeof(tmp)))\n'
    '                        errno = -EFAULT;\n'
    '        }\n'
    '#else\n'
    '        if (copy_to_user(name, utsname(), sizeof *name))\n'
    '                errno = -EFAULT;\n'
    '#endif\n'
    '        up_read(&uts_sem);',
    'sys.c: newuname spoofing')

# 4. fs/namespace.c - clone_mnt RKP-safe hook
# We anchor on the alloc_vfsmnt call which is outside the RKP ifdef block
fix('fs/namespace.c',
    '        mnt = alloc_vfsmnt(old->mnt_devname);',
    '        mnt = alloc_vfsmnt(old->mnt_devname);\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
    '        if (likely(!IS_ERR(mnt)))\n'
    '                susfs_clone_mnt_fix(old, mnt);\n'
    '#endif',
    'namespace.c: clone_mnt mnt fix')
