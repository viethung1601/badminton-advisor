class ListRackets:
    def __init__(self, repo): self.repo = repo
    def __call__(self, **query) -> dict: return self.repo.list_page(**query)

class ListShoes:
    def __init__(self, repo): self.repo = repo
    def __call__(self, **query) -> dict: return self.repo.list_page(**query)