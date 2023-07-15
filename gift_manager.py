import json
from collections import defaultdict
import typing as tp
import re


class FileJSON:
    def __init__(self, path, init_structure, load = json.loads, dump = json.dumps):
        self.path = path
        self.init_structure = init_structure
        self.contents = open(self.path, encoding = "utf-8").read()
        self.json = load(self.contents)
        self.dump = dump
    
    def save(self):
        self.contents = self.dump(self.json, indent = 2)
        with open(self.path, "w", encoding = "utf-8") as saved_file:
            saved_file.write(self.contents)
            saved_file.close()
    
    def set_init_structure(self, save = True):
        self.json = self.init_structure
        if save:
            self.save()


class MessagesJSON(FileJSON):
    def __init__(self):
        super().__init__(
            path = "messages.json",
            init_structure = {},
            load = lambda c: {eval(k): v for (k, v) in json.loads(c).items()},
            dump = lambda d, **kw: json.dumps({str(k): v for (k, v) in d.items()}, **kw)
        )


class GiftsJSON(FileJSON):
    def __init__(self):
        super().__init__(path = "gifts.json", init_structure = {
            "gifts": [],
            "person_matching": {}
        })
    
    @staticmethod
    def map_gift_to_count(people: 'PeopleJSON') -> tp.Dict[str, int]:
        user_selected_gifts = defaultdict(int)
        for user in people.json["users"]:
            for gift in people.json["users"][user]["selected_gifts"]:
                user_selected_gifts[gift] += people.json["users"][user]["selected_gifts"][gift]["count"]
        return user_selected_gifts
    
    def get_available_gifts_for_user(self, people: 'PeopleJSON', user_id, user_name) -> tp.Dict[str, tp.Any]:
        gift_to_count = self.map_gift_to_count(people)
        globally_available = [
            gift for gift in self.json["gifts"] if gift_to_count[gift["id"]] < gift["total_count"]
        ]
        user_gifts = people.json["users"][user_id]["selected_gifts"]
        user_available = [
            gift for gift in globally_available if user_gifts.get(gift["id"], {"count": 0})["count"] < gift["count_per_user"]
        ]
        matching = self.json["person_matching"]
        for (pattern, pattern_matched_gifts) in matching.items():
            if re.search(pattern, user_name):
                return [gift for gift in user_available if gift["id"] in pattern_matched_gifts]
        return user_available


class PeopleJSON(FileJSON):
    def __init__(self):
        super().__init__(path = "people.json", init_structure = {
            "users": {}
        })
    
    def add_user(self, user_id, user_name = None, save = True):
        if str(user_id) not in self.json["users"]:
            self.json["users"][str(user_id)] = {
                "selected_gifts": {},
                "user_name": user_name,
                "sent_once": False
            }
        if save:
            self.save()
    
    def select_gift(self, gift_id, user_id, save = True):
        if gift_id not in self.json["users"][user_id]["selected_gifts"]:
            self.json["users"][user_id]["selected_gifts"][gift_id] = {
                "count": 1
            }
        else:
            self.json["users"][user_id]["selected_gifts"][gift_id]["count"] += 1
        if save:
            self.save()


if __name__ == "__main__":
    people = PeopleJSON()
    people.set_init_structure()
    gifts = GiftsJSON()
    people.add_user("gleb")
    people.add_user("fedya")
    people.select_gift("electric_razor", "gleb")
    people.select_gift("electric_razor", "fedya")
    gifts.get_available_gifts_for_user(people, "fedya")
