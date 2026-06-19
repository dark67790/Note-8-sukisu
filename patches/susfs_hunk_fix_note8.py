# Your original code had this duplicate replacement argument:
fix('fs/stat.c',
    '\tstat->blksize = i_blocksize(inode);\n' # 1: path
    '\tstat->blocks = inode->i_blocks;\n'    # 2: old anchor
    '}',
    '\tstat->blksize = i_blocksize(inode);\n' # 3: new string
    '\tstat->blocks = inode->i_blocks;\n'
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'
    '\tsusfs_sus_kstat_spoof_generic_fillattr(inode, stat);\n'
    '#endif\n'
    '}',
    '#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n'     # 4: accidental duplicate (causing TypeError)
    '\tsusfs_sus_kstat_spoof_generic_fillattr(inode, stat);\n'
    '#endif\n'
    '}',
    'stat.c hunk#2: generic_fillattr SUS_KSTAT spoof call') # 5: label
