import sys

def inject_at_line(file_path, line_num, injection, desc):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Insert the code AFTER the specified line
    lines.insert(line_num, injection + "\n")
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
    print(f"SUCCESS: {desc}")

# 1. dcache.c: __d_lookup_rcu
inject_at_line('fs/dcache.c', 2232, 
               '#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n'
               '                if (dentry->d_inode && unlikely(dentry->d_inode->i_state & INODE_STATE_SUS_PATH) && likely(current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC))\n'
               '                        continue;\n'
               '#endif', 'dcache.c fix')

# 2. namei.c: do_filp_open (Targeting the one at 3440)
inject_at_line('fs/namei.c', 3440,
               '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n'
               'extern struct filename* susfs_get_redirected_path(unsigned long ino);\n'
               '#endif', 'namei.c fix')

# 3. sys.c: newuname (Targeting the first occurrence at 1344)
inject_at_line('kernel/sys.c', 1344,
               '#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n'
               'extern void susfs_spoof_uname(struct new_utsname* tmp);\n'
               '#endif', 'sys.c fix')

# 4. namespace.c: clone_mnt (Targeting the one at 1372)
inject_at_line('fs/namespace.c', 1373,
               '#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n'
               '        if (likely(!IS_ERR(mnt)))\n'
               '                susfs_clone_mnt_fix(old, mnt);\n'
               '#endif', 'namespace.c fix')
