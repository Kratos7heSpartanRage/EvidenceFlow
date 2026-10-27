"""Offline repository adapter that enforces the service persistence contracts."""


class MemoryRepository:
    """Test adapter only; production transaction/concurrency behavior is untested."""

    def __init__(self):
        self.evaluations = {}
        self.snapshots = {}
        self.suggestions = {}
        self.annotations = {}
        self.human_decisions = {1: "exclude"}
        self.human_annotations = {1: "Reviewer-corrected population"}

    @staticmethod
    def insert(table, key, value):
        if key in table and table[key] != value:
            raise ValueError("Immutable key cannot be overwritten")
        table.setdefault(key, value)

    def save_pair_evaluation(self, evaluation):
        self.insert(self.evaluations, evaluation.input_fingerprint, evaluation)

    def save_group_snapshot(self, run_id, groups):
        self.insert(self.snapshots, run_id, groups)

    def get_suggestion(self, key):
        return self.suggestions.get(key)

    def save_suggestion(self, key, suggestion):
        self.insert(self.suggestions, key, suggestion)

    def get_machine_annotations(self, key):
        return self.annotations.get(key)

    def save_machine_annotations(self, key, annotations):
        self.insert(self.annotations, key, annotations)
