from ...git.services.repositories import get_repository_branches  # assuming you have this

def select_branch(owner: str, repo: str, token: str) -> str:
    branches = get_repository_branches(owner, repo, token)
    print("\nAvailable branches:")
    for idx, b in enumerate(branches, start=1):
        print(f"{idx}. {b.name}")
    choice = int(input("\nSelect branch number: ")) - 1
    return branches[choice].name
