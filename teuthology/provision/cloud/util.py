import os


def get_user_ssh_pubkey(path='~/.ssh/id_rsa.pub'):
    full_path = os.path.expanduser(path)
    if not os.path.exists(full_path):
        return
    with file(full_path, 'rb') as f:
        return f.read().strip()