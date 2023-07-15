from gift_manager import PeopleJSON, MessagesJSON

people = PeopleJSON()
messages = MessagesJSON()

people.set_init_structure()
people.save()

messages.set_init_structure()
messages.save()