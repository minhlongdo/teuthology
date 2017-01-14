"""
Internal tasks  for redhat downstream builds
"""
import contextlib
import logging
import requests
from tempfile import NamedTemporaryFile
from teuthology.parallel import parallel
from teuthology.orchestra import run

log = logging.getLogger(__name__)


@contextlib.contextmanager
def setup_cdn_repo(ctx, config):
    """
     setup repo if set_cdn_repo exists in config
     set_cdn_repo:
        rhbuild: 2.0 or 1.3.2 or 1.3.3
    """
    # do import of tasks here since the qa task path should be set here
    if ctx.config.get('set-cdn-repo'):
        from tasks.set_repo import set_cdn_repo
        config = ctx.config.get('set-cdn-repo')
        set_cdn_repo(ctx, config)
    yield


@contextlib.contextmanager
def setup_additional_repo(ctx, config):
    """
    set additional repo's for testing
    config:
      set-add-repo: 'http://example.com/internal.repo'
    """
    if ctx.config.get('set-add-repo'):
        add_repo = ctx.config.get('set-add-repo')
        for remote in ctx.cluster.remotes.iterkeys():
            if remote.os.package_type == 'rpm':
                remote.run(args=['sudo', 'wget', '-O', '/etc/yum.repos.d/add.repo',
                                 add_repo])
                remote.run(args=['sudo', 'yum', 'update', 'metadata'])

    yield


@contextlib.contextmanager
def setup_base_repo(ctx, config):
    """
    Setup repo based on redhat nodes
    Config:
      base_url:  base url that provides Mon, OSD, Tools etc
      installer_url: Installer url that provides Agent, Installer
    """
    if not ctx.config.get('base_repo_url'):
        # no repo defined
        yield
    if ctx.config.get('set-cdn-repo'):
        log.info("CDN repo already set, skipping rh repo")
        yield
    else:
        _setup_latest_repo(ctx, config)
        try:
            yield
        finally:
            log.info("Cleaning up repo's")
            for remote in ctx.cluster.remotes.iterkeys():
                if remote.os.package_type == 'rpm':
                    remote.run(args=['sudo', 'rm',
                                     run.Raw('/etc/yum.repos.d/rh*.repo'),
                                     ], check_status=False)


def _setup_latest_repo(ctx, config):
    """
    Setup repo based on redhat nodes
    """
    with parallel():
        for remote in ctx.cluster.remotes.iterkeys():
            if remote.os.package_type == 'rpm':
                remote.run(args=['sudo', 'subscription-manager', 'repos',
                                 run.Raw('--disable=*ceph*')])
                base_url = ctx.config.get('base_repo_url', '')
                installer_url = ctx.config.get('installer_repo_url', '')
                repos = ['MON', 'OSD', 'Tools', 'Calamari', 'Installer']
                installer_repos = ['Agent', 'Main', 'Installer']
                if ctx.config.get('base_rh_repos'):
                    repos = ctx.config.get('base_rh_repos')
                if ctx.config.get('installer_repos'):
                    installer_repos = ctx.config.get('installer_repos')
                # create base repo
                if base_url.startswith('http'):
                    repo_to_use = _get_repos_to_use(base_url, repos)
                    base_repo_file = NamedTemporaryFile(delete=False)
                    _create_temp_repo_file(repo_to_use, base_repo_file)
                    remote.put_file(base_repo_file.name, base_repo_file.name)
                    remote.run(args=['sudo', 'cp', base_repo_file.name,
                                     '/etc/yum.repos.d/rh_ceph.repo'])
                if installer_url.startswith('http'):
                    irepo_to_use = _get_repos_to_use(
                        installer_url, installer_repos)
                    installer_file = NamedTemporaryFile(delete=False)
                    _create_temp_repo_file(irepo_to_use, installer_file)
                    remote.put_file(installer_file.name, installer_file.name)
                    remote.run(args=['sudo', 'cp', installer_file.name,
                                     '/etc/yum.repos.d/rh_inst.repo'])


def _get_repos_to_use(base_url, repos):
    repod = dict()
    for repo in repos:
        repo_to_use = base_url + "compose/" + repo + "/x86_64/os/"
        r = requests.get(repo_to_use)
        log.info("Checking %s", repo_to_use)
        if r.status_code == 200:
            log.info("Using %s", repo_to_use)
            repod[repo] = repo_to_use
    return repod


def _create_temp_repo_file(repos, repo_file):
    for repo in repos.keys():
        header = "[ceph-" + repo + "]" + "\n"
        name = "name=ceph-" + repo + "\n"
        baseurl = "baseurl=" + repos[repo] + "\n"
        gpgcheck = "gpgcheck=0\n"
        enabled = "enabled=1\n\n"
        repo_file.write(header)
        repo_file.write(name)
        repo_file.write(baseurl)
        repo_file.write(gpgcheck)
        repo_file.write(enabled)
    repo_file.close()
