from django.test import SimpleTestCase


class CommitteesCollaborationsDuplicateTests(SimpleTestCase):
    def dedup(self, names, ids):
        seen = set()
        uniq_names = []
        uniq_ids = []
        for name, id_ in zip(names, ids):
            key = name.lower()
            if key not in seen:
                seen.add(key)
                uniq_names.append(name)
                uniq_ids.append(id_)
        return uniq_names, uniq_ids

    def test_dedup_case_insensitive(self):
        names = ["Org A", "org a", "Org B", "ORG B"]
        ids = ["1", "2", "3", "3"]
        uniq_names, uniq_ids = self.dedup(names, ids)
        self.assertEqual(uniq_names, ["Org A", "Org B"])
        self.assertEqual(uniq_ids, ["1", "3"])
