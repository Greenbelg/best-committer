import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
import bar

oauth_token = ""
ORG = "Docker"
all_committers = set()


def get_repos():
    has_next_page = True
    repos = []
    end_repo = None
    while has_next_page:
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        data = session.post(url='https://api.github.com/graphql',
                            json={"query": make_query_repos(end_repo)},
                            headers={"Authorization": "Bearer {}".format(oauth_token)},
                            ).json()
        has_next_page = data['data']['organization']['repositories']['pageInfo']['hasNextPage']
        for repo in data['data']['organization']['repositories']['nodes']:
            repos.append(repo['name'])

        end_repo = data['data']['organization']['repositories']['pageInfo']['endCursor']

    return repos


def get_branches(repo):
    has_next_page = True
    branches = []
    end_branch = None
    while has_next_page:
        try:
            session = requests.Session()
            retry = Retry(connect=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            data = session.post(
                url='https://api.github.com/graphql',
                json={"query": make_query_branches(repo, end_branch)},
                headers={"Authorization": "Bearer {}".format(oauth_token)},
            ).json()
            has_next_page = data['data']['repository']['refs']['pageInfo']['hasNextPage']
            for branch in data['data']['repository']['refs']['nodes']:
                branches.append(branch['name'])
            end_branch = data['data']['repository']['refs']['pageInfo']['endCursor']
        except KeyError:
            has_next_page = False
            continue

    return branches


def get_authors(repo, branch):
    has_next_page = True
    end_commit = None
    while has_next_page:
        try:
            session = requests.Session()
            retry = Retry(connect=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            data = session.post(
                url='https://api.github.com/graphql',
                json={"query": make_query_commits(repo, branch, end_commit)},
                headers={"Authorization": "Bearer {}".format(oauth_token)},
            ).json()
            has_next_page = data['data']['repository']['ref']['target']['history']['pageInfo']['hasNextPage']
            for commit in data['data']['repository']['ref']['target']['history']['nodes']:
                if commit['parents']['totalCount'] < 2:
                    all_committers.add((commit['author']['email'], commit['oid']))
            end_commit = data['data']['repository']['ref']['target']['history']['pageInfo']['endCursor']
        except KeyError:
            has_next_page = False
            continue


def make_query_repos(repo=None):
    return '''
{
  organization(login:ORG) {
    repositories(first: 10, after:After) {
      pageInfo {
      	endCursor
      	hasNextPage
      }
      nodes{
        name
      }
    }
  }
}
'''.replace("ORG", '"{}"'.format(ORG)) \
        .replace("After", '"{}"'.format(repo) if repo else "null")


def make_query_branches(repo, branch=None):
    return '''
{
  repository(owner: ORG, name: REPO) {
    refs(refPrefix: "refs/heads/", first: 100, after:AFTER) {
      nodes {
        name
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
'''.replace("ORG", '"{}"'.format(ORG)) \
        .replace("REPO", '"{}"'.format(repo)) \
        .replace("AFTER", '"{}"'.format(branch) if branch else "null")


def make_query_commits(repo, branch, commit=None):
    return '''
{
    repository(owner:ORG, name: REPO) {
      ref(qualifiedName: "refs/heads/BRANCH") {
        target {
          ... on Commit {
            history(first: 100, after:AFTER) {
              nodes {
                oid
                author {
                  email
                }
                parents{
                  totalCount
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
      }
    }
  }
'''.replace("ORG", '"{}"'.format(ORG)) \
        .replace("REPO", '"{}"'.format(repo)) \
        .replace("BRANCH", branch) \
        .replace("AFTER", '"{}"'.format(commit) if commit else "null")


def find_authors(repo, branches):
    for branch in branches:
        get_authors(repo, branch)


def main(token):
    global oauth_token
    oauth_token = token
    repos = get_repos()
    threads = []
    for _, repo in enumerate(repos):
        branches = get_branches(repo)
        threads.append(threading.Thread(target=find_authors, args=(repo, branches), daemon=True))
        threads[-1].start()

    for thread in threads:
        thread.join()

    count_commits_by_author = {}
    for author, commit in all_committers:
        if author not in count_commits_by_author:
            count_commits_by_author[author] = 0
        count_commits_by_author[author] += 1
    count_commits_by_author = dict(sorted(count_commits_by_author.items(),
                                          key=lambda item: item[1], reverse=True))
    names = []
    weights = []
    for i, (author, count) in enumerate(count_commits_by_author.items()):
        if i > 99:
            break
        names.append(author)
        weights.append(count)

    bar.show(names, weights)


if __name__ == "__main__":
    main(sys.argv[1])
