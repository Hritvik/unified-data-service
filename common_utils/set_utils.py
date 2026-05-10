from typing import Any, List, Optional, Set


class SetGroup:
    def __init__(self, set_list: List[Set[Any]]) -> None:
        self.set_list = set_list
        self.element_to_set: dict[Any, int] = {}
        for i, s in enumerate(set_list):
            for elem in s:
                self.element_to_set[elem] = i

    def are_in_same_set(self, a: Any, b: Any) -> bool:
        set_a = self.element_to_set.get(a)
        set_b = self.element_to_set.get(b)
        return set_a is not None and set_b is not None and set_a == set_b

    def shares_set_with_any(self, a: Any, b_list: List[Any]) -> bool:
        set_id = self.element_to_set.get(a)
        if set_id is None:
            return False
        return any(self.element_to_set.get(b) == set_id for b in b_list)

    def get_set(self, element: Any) -> Optional[Set[Any]]:
        set_id = self.element_to_set.get(element)
        return self.set_list[set_id] if set_id is not None else None
