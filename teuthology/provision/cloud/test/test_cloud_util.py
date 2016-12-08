from mock import patch, MagicMock
from pytest import mark

from teuthology.provision.cloud import util


@mark.parametrize(
    'path, exists',
    [
        ('/fake/path', True),
        ('/fake/path', False),
    ]
)
def test_get_user_ssh_pubkey(path, exists):
    with patch('os.path.exists') as m_exists:
        m_exists.return_value = exists
        with patch('teuthology.provision.cloud.util.file') as m_file:
            m_file.return_value = MagicMock(spec=file)
            util.get_user_ssh_pubkey(path)
            if exists:
                assert m_file.called_once_with(path, 'rb')

